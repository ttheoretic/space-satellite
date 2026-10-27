"""
Der "Missionskern": verbindet Uhr, Bahndaten, Simulator, Datenbank und
WebSocket-Verteiler und betreibt die Hintergrundschleifen.

Es gibt genau ein Mission-Objekt pro Server (siehe ``mission`` ganz unten).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from . import audit
from . import commands as cmd
from .clock import MissionClock, as_utc, iso, parse_iso
from .config import settings
from .db import session_scope
from .limits import AlarmEngine, LimitSet
from .models import Command, Setting, TelemetryFrame
from .orbit.passes import GroundStation, PassPredictor, look_angles, pass_track
from .orbit.tle import TleManager
from .parameters import PARAMETERS_BY_KEY
from .simulator.cubesat import CubeSatSimulator
from .sources import TelemetrySource
from .ws import Broadcaster

log = logging.getLogger(__name__)

CLOCK_KEY = "clock_offset_s"
STATION_KEY = "ground_station"
MAX_FAST_FORWARD = timedelta(hours=24)


class Mission:
    def __init__(self) -> None:
        self.clock = MissionClock()
        self.tle = TleManager()
        self.simulator = CubeSatSimulator(lambda: self.tle.current.satellite)
        self.alarms = AlarmEngine()
        self.passes = PassPredictor()
        self.station = GroundStation(settings.station_name, settings.station_lat_deg,
                                     settings.station_lon_deg, settings.station_alt_m)
        self._in_contact: bool | None = None
        self.broadcaster = Broadcaster()
        self.latest_frame: dict | None = None
        self._tasks: list[asyncio.Task] = []

    # ------------------------------------------------------- Lebenszyklus
    @property
    def source(self) -> TelemetrySource:
        """Woher die Telemetrie kommt. Im Prototyp immer der Simulator."""
        return self.simulator

    async def start(self) -> None:
        self.alarms.load()
        self._restore_station()
        self._restore_clock()
        self._backfill_if_empty()
        self._tasks = [
            asyncio.create_task(self._telemetry_loop(), name="telemetry"),
            asyncio.create_task(self._tle_loop(), name="tle"),
            asyncio.create_task(self._housekeeping_loop(), name="housekeeping"),
        ]

    async def stop(self) -> None:
        self._save_clock()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    # ------------------------------------------------------ Statusabfrage
    def status(self) -> dict:
        now = self.clock.now()
        return {
            "satellite": {"name": settings.satellite_name, "norad_id": settings.norad_id},
            "station": self.station.to_dict(),
            "clock": {
                "mission_time": iso(now),
                "speed": self.clock.speed,
                "speed_options": list(settings.speed_options),
            },
            "tle": {**self.tle.current.status(now), "last_error": self.tle.last_error},
            "simulator": {"random_faults": self.simulator.random_faults_enabled},
        }

    async def broadcast_status(self) -> None:
        await self.broadcaster.broadcast({"type": "status", "status": self.status()})

    # ----------------------------------------------------- Steuerbefehle
    async def set_speed(self, speed: int) -> None:
        if speed not in settings.speed_options:
            raise ValueError(f"Speed must be one of {settings.speed_options}")
        self.clock.set_speed(speed)
        self._save_clock()
        await self.broadcast_status()

    async def reset(self) -> None:
        """Demo zurücksetzen: Telemetrie löschen, Uhr auf Echtzeit, frischer Satellit."""
        with session_scope() as s:
            s.execute(delete(TelemetryFrame))
            s.execute(delete(Command))
        self.alarms.reset()
        self.clock = MissionClock()
        self.simulator = CubeSatSimulator(lambda: self.tle.current.satellite)
        self._save_clock()
        self._backfill_if_empty()
        await self.broadcaster.broadcast({"type": "reload"})
        await self.broadcast_status()

    # ---------------------------------------------------------- Simulator
    async def trigger_fault(self, key: str) -> None:
        self.simulator.trigger_fault(key)
        await self._flush_events()

    async def clear_faults(self) -> None:
        self.simulator.clear_faults()
        await self._flush_events()

    async def set_random_faults(self, enabled: bool) -> None:
        self.simulator.random_faults_enabled = enabled
        await self.broadcast_status()

    # ------------------------------------------------- Alarme & Grenzwerte
    async def acknowledge(self, alarm_ids: list[int] | None, user: str) -> list[dict]:
        now = self.clock.now()
        acked = self.alarms.acknowledge(alarm_ids, user, now)
        if acked:
            audit.record(user, "alarm.ack", now,
                         alarms=[f"#{a['id']} {a['param_label']}" for a in acked])
        for a in acked:
            await self.broadcaster.broadcast({"type": "alarm", "alarm": a})
        return acked

    async def update_limits(self, key: str, limits: LimitSet, user: str) -> None:
        now = self.clock.now()
        self.alarms.update_limits(key, limits, user, now)
        audit.record(user, "limits.update", now, param=key,
                     label=PARAMETERS_BY_KEY[key].label,
                     crit_low=limits.crit_low, warn_low=limits.warn_low,
                     warn_high=limits.warn_high, crit_high=limits.crit_high,
                     enabled=limits.enabled)
        await self.broadcaster.broadcast({"type": "limits", "limits": self.alarms.limits_catalog()})

    # ------------------------------------------------ Überflüge & Station
    def get_passes(self, hours: float = 48) -> list[dict]:
        return self.passes.get(self.tle.current.satellite, self.station, self.clock.now(), hours)

    def get_pass_track(self, pass_id: str) -> dict | None:
        p = next((p for p in self.get_passes(48) if p["id"] == pass_id), None)
        if p is None:
            return None
        track = pass_track(self.tle.current.satellite, self.station,
                           parse_iso(p["aos"]), parse_iso(p["los"]))
        return {**p, "track": track}

    async def update_station(self, station: GroundStation, user: str) -> None:
        station.validate()
        self.station = station
        self.passes.invalidate()
        self._in_contact = None
        with session_scope() as s:
            s.merge(Setting(key=STATION_KEY, value=station.to_dict()))
        audit.record(user, "station.update", self.clock.now(), **station.to_dict())
        await self.broadcast_status()

    async def jump_to_next_pass(self, lead_s: int = 60) -> dict:
        """Demo: Missionszeit bis kurz vor den nächsten Überflug vorspulen.
        Die übersprungene Zeit wird im Schnelldurchlauf simuliert, damit
        Verlauf, Eklipsen und Alarme lückenlos bleiben."""
        now = self.clock.now()
        upcoming = [p for p in self.get_passes(48)
                    if parse_iso(p["aos"]) > now + timedelta(seconds=lead_s + 5)]
        if not upcoming:
            raise ValueError("No upcoming pass in the next 48 hours")
        target = parse_iso(upcoming[0]["aos"]) - timedelta(seconds=lead_s)
        if target - now > MAX_FAST_FORWARD:
            raise ValueError("Next pass is more than 24 hours away")
        await self._fast_forward(target)
        return upcoming[0]

    # ------------------------------------------------------------- Befehle
    def list_commands(self) -> list[dict]:
        return cmd.list_all(self.clock.now())

    async def create_command(self, code: str, args: dict, pass_id: str | None, comment: str,
                             user: str) -> dict:
        clean = cmd.validate(code, args)
        now = self.clock.now()
        p = self._schedulable_pass(pass_id) if pass_id else None
        with session_scope() as s:
            c = Command(code=code, args=clean, comment=comment.strip(), status=cmd.AWAITING,
                        created_by=user, created_at=now)
            if p:
                c.pass_id, c.pass_aos, c.pass_los = p["id"], parse_iso(p["aos"]), parse_iso(p["los"])
            s.add(c)
            s.flush()
            result = cmd.to_dict(c, now)
        audit.record(user, "command.create", now, command=f"#{result['id']} {result['text']}",
                     pass_id=pass_id, comment=result["comment"])
        await self.broadcaster.broadcast({"type": "command", "command": result})
        return result

    async def schedule_command(self, command_id: int, pass_id: str, user: str) -> dict:
        p = self._schedulable_pass(pass_id)

        def change(c: Command, now: datetime) -> None:
            if c.status in cmd.FINAL:
                raise cmd.CommandError(f"Command is already {c.status.replace('_', ' ')}")
            c.pass_id, c.pass_aos, c.pass_los = p["id"], parse_iso(p["aos"]), parse_iso(p["los"])

        return await self._command_action(command_id, user, "command.schedule", change,
                                          pass_id=pass_id)

    async def approve_command(self, command_id: int, user: str) -> dict:
        def change(c: Command, now: datetime) -> None:
            if c.status != cmd.AWAITING:
                raise cmd.CommandError("Only commands awaiting approval can be approved")
            if c.created_by == user:
                raise cmd.CommandError("Four-eyes principle: a second person must approve "
                                       "this command, not its author")
            c.status, c.decided_by, c.decided_at = cmd.APPROVED, user, now

        return await self._command_action(command_id, user, "command.approve", change)

    async def reject_command(self, command_id: int, reason: str, user: str) -> dict:
        if not reason.strip():
            raise cmd.CommandError("Please give a reason for the rejection")

        def change(c: Command, now: datetime) -> None:
            if c.status != cmd.AWAITING:
                raise cmd.CommandError("Only commands awaiting approval can be rejected")
            c.status, c.decided_by, c.decided_at = cmd.REJECTED, user, now
            c.reject_reason = reason.strip()

        return await self._command_action(command_id, user, "command.reject", change,
                                          reason=reason.strip())

    async def cancel_command(self, command_id: int, user: str) -> dict:
        def change(c: Command, now: datetime) -> None:
            if c.status in cmd.FINAL:
                raise cmd.CommandError(f"Command is already {c.status.replace('_', ' ')}")
            c.status = cmd.CANCELLED

        return await self._command_action(command_id, user, "command.cancel", change)

    async def send_command(self, command_id: int, user: str) -> dict:
        """Senden (simuliert) – nur freigegeben und nur während des zugewiesenen Überflugs."""

        def change(c: Command, now: datetime) -> None:
            if c.status != cmd.APPROVED:
                raise cmd.CommandError("Only approved commands can be sent")
            if not c.pass_aos or not c.pass_los:
                raise cmd.CommandError("Assign the command to a pass first")
            if not as_utc(c.pass_aos) <= now <= as_utc(c.pass_los):
                raise cmd.CommandError("No contact: commands can only be sent during their pass")
            if not look_angles(self.tle.current.satellite, self.station, now)["in_contact"]:
                raise cmd.CommandError("No contact with the spacecraft right now")
            c.result = self.source.send_command(c.code, c.args)
            c.status, c.sent_by, c.sent_at = cmd.SENT, user, now

        result = await self._command_action(command_id, user, "command.send", change)
        await self._flush_events()
        return result

    def _schedulable_pass(self, pass_id: str) -> dict:
        p = next((p for p in self.get_passes(48) if p["id"] == pass_id), None)
        if p is None:
            raise cmd.CommandError(f"Pass {pass_id} is not an upcoming pass")
        return p

    async def _command_action(self, command_id: int, user: str, action: str, change,
                              **details) -> dict:
        """Gemeinsamer Ablauf: Befehl laden, Regel prüfen und ändern,
        protokollieren und an alle Browser melden."""
        now = self.clock.now()
        with session_scope() as s:
            c = s.get(Command, command_id)
            if c is None:
                raise KeyError(command_id)
            change(c, now)
            s.flush()
            result = cmd.to_dict(c, now)
        audit.record(user, action, now, command=f"#{result['id']} {result['text']}",
                     result=result["result"], **details)
        await self.broadcaster.broadcast({"type": "command", "command": result})
        return result

    async def refresh_tle(self) -> bool:
        ok = await self.tle.refresh_online()
        await self.broadcast_status()
        return ok

    # ------------------------------------------------- Hintergrundschleifen
    async def _telemetry_loop(self) -> None:
        """Erzeugt jede Sekunde ein Telemetrie-Paket, speichert und verteilt es."""
        while True:
            try:
                now = self.clock.now()
                frame = self.source.step_to(now)
                changed_alarms = self.alarms.process(frame, now)  # ergänzt frame["limits"]
                frame["contact"] = self._contact(now)
                self.latest_frame = frame
                self._store(frame)
                await self.broadcaster.broadcast({"type": "telemetry", "frame": frame})
                for alarm in changed_alarms:
                    await self.broadcaster.broadcast({"type": "alarm", "alarm": alarm})
                await self._flush_events()
            except Exception:
                log.exception("Fehler in der Telemetrie-Schleife")
            await asyncio.sleep(settings.tick_seconds)

    async def _tle_loop(self) -> None:
        """Lädt die TLE beim Start und danach regelmäßig neu."""
        while True:
            await self.refresh_tle()
            await asyncio.sleep(settings.tle_refresh_hours * 3600)

    async def _housekeeping_loop(self) -> None:
        """Alte Telemetrie löschen, Uhrstand sichern."""
        while True:
            await asyncio.sleep(30)
            try:
                cutoff = self.clock.now() - timedelta(hours=settings.retention_hours)
                with session_scope() as s:
                    s.execute(delete(TelemetryFrame).where(TelemetryFrame.timestamp < cutoff))
                self._save_clock()
            except Exception:
                log.exception("Fehler bei der Datenpflege")

    # ---------------------------------------------------------- Interna
    def _contact(self, now: datetime) -> dict:
        """Sichtbarkeit von der Bodenstation; meldet Kontaktbeginn/-ende als Ereignis."""
        contact = look_angles(self.tle.current.satellite, self.station, now)
        if self._in_contact is not None and contact["in_contact"] != self._in_contact:
            text = (f"AOS – contact with {self.station.name}" if contact["in_contact"]
                    else f"LOS – contact with {self.station.name} ended")
            self.simulator.add_event("info", text)
        self._in_contact = contact["in_contact"]
        return contact

    async def _fast_forward(self, target: datetime) -> None:
        t = self.clock.now()
        frames = []
        while t < target:
            t = min(t + timedelta(seconds=60), target)
            frame = self.source.step_to(t, random_faults=False)
            self.alarms.process(frame, t)
            frames.append(frame)
        with session_scope() as s:
            s.add_all(TelemetryFrame(timestamp=parse_iso(f["t"]), data=f) for f in frames)
        self.clock.jump_to(target)
        self._save_clock()
        self._in_contact = None
        if frames:
            self.latest_frame = frames[-1]
        self.source.pop_new_events()  # stehen im Ereignisprotokoll, nicht einzeln senden
        log.info("Vorgespult: %d Pakete bis %s", len(frames), iso(target))
        await self.broadcaster.broadcast({"type": "reload"})
        await self.broadcast_status()

    async def _flush_events(self) -> None:
        for event in self.source.pop_new_events():
            await self.broadcaster.broadcast({"type": "event", "event": event})

    def _store(self, frame: dict) -> None:
        with session_scope() as s:
            s.add(TelemetryFrame(timestamp=parse_iso(frame["t"]), data=frame))

    def _backfill_if_empty(self) -> None:
        """Beim ersten Start die letzten Stunden vorsimulieren, damit die
        Diagramme sofort etwas zeigen (ohne zufällige Fehler)."""
        with session_scope() as s:
            if s.scalar(select(func.count()).select_from(TelemetryFrame)):
                return
        end = self.clock.now()
        t = end - timedelta(hours=settings.backfill_hours)
        frames = []
        while t < end:
            frame = self.source.step_to(t, random_faults=False)
            frame["limits"] = {}
            frames.append(frame)
            t += timedelta(seconds=30)
        with session_scope() as s:
            s.add_all(TelemetryFrame(timestamp=parse_iso(f["t"]), data=f)
                      for f in frames)
        self.latest_frame = frames[-1] if frames else None
        self.source.pop_new_events()  # Vorlauf-Ereignisse nicht live senden
        log.info("Vorlauf: %d Pakete simuliert", len(frames))

    def _restore_clock(self) -> None:
        """Missionszeit nach einem Neustart fortsetzen (Zeitraffer startet bei 1×)."""
        with session_scope() as s:
            row = s.get(Setting, CLOCK_KEY)
            offset = float(row.value) if row else 0.0
        self.clock = MissionClock(datetime.now(timezone.utc) + timedelta(seconds=offset))

    def _restore_station(self) -> None:
        """Zuletzt eingestellte Bodenstation laden (sonst Standard aus config.py)."""
        with session_scope() as s:
            row = s.get(Setting, STATION_KEY)
            if row:
                self.station = GroundStation(**row.value)

    def _save_clock(self) -> None:
        with session_scope() as s:
            s.merge(Setting(key=CLOCK_KEY, value=self.clock.offset_seconds()))


mission = Mission()
