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
from .clock import MissionClock, iso, parse_iso
from .config import settings
from .db import session_scope
from .limits import AlarmEngine, LimitSet
from .models import Setting, TelemetryFrame
from .orbit.tle import TleManager
from .parameters import PARAMETERS_BY_KEY
from .simulator.cubesat import CubeSatSimulator
from .sources import TelemetrySource
from .ws import Broadcaster

log = logging.getLogger(__name__)

CLOCK_KEY = "clock_offset_s"


class Mission:
    def __init__(self) -> None:
        self.clock = MissionClock()
        self.tle = TleManager()
        self.simulator = CubeSatSimulator(lambda: self.tle.current.satellite)
        self.alarms = AlarmEngine()
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
            "station": {
                "name": settings.station_name,
                "lat": settings.station_lat_deg,
                "lon": settings.station_lon_deg,
                "alt_m": settings.station_alt_m,
            },
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
        self.alarms.reset()
        self.clock = MissionClock()
        self.simulator = CubeSatSimulator(lambda: self.tle.current.satellite)
        self._save_clock()
        self._backfill_if_empty()
        await self.broadcaster.broadcast({"type": "reset"})
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

    def _save_clock(self) -> None:
        with session_scope() as s:
            s.merge(Setting(key=CLOCK_KEY, value=self.clock.offset_seconds()))


mission = Mission()
