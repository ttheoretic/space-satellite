"""
Grenzwertprüfung und Alarmlogik.

Für jeden Messwert gibt es bis zu vier Grenzen:

    crit_low   warn_low                warn_high   crit_high
  ────┼──────────┼─────────── gut ─────────┼───────────┼────
  rot │   gelb   │                         │   gelb    │ rot

Hysterese: Ein Alarm geht nicht schon weg, wenn der Wert die Grenze gerade so
wieder unterschreitet, sondern erst, wenn er ein kleines Stück ("Totband")
zurück im guten Bereich ist. Ohne Hysterese würde ein rauschender Wert direkt
an der Grenze ständig neue Alarme erzeugen ("Alarmflattern"). Verschlechterungen
werden dagegen sofort gemeldet.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy import delete, select

from .clock import iso, iso_or_none
from .db import session_scope
from .models import Alarm, Limit
from .parameters import PARAMETERS, PARAMETERS_BY_KEY

RANK = {"ok": 0, "warning": 1, "critical": 2}
HYSTERESIS_FRACTION = 0.02  # Totband = 2 % der Spanne zwischen den Grenzen


@dataclass
class LimitSet:
    crit_low: float | None = None
    warn_low: float | None = None
    warn_high: float | None = None
    crit_high: float | None = None
    enabled: bool = True

    def defined(self) -> list[float]:
        return [v for v in (self.crit_low, self.warn_low, self.warn_high, self.crit_high)
                if v is not None]

    def is_empty(self) -> bool:
        return not self.defined()

    def deadband(self) -> float:
        vals = self.defined()
        if not vals:
            return 0.0
        span = max(vals) - min(vals) if len(vals) > 1 else abs(vals[0])
        return max(span * HYSTERESIS_FRACTION, 1e-6)

    def classify(self, value: float, margin: float = 0.0) -> tuple[str, str]:
        """Stufe ("ok" | "warning" | "critical") und verletzte Grenze als Text.
        Mit margin > 0 werden die Grenzen um das Totband nach innen verschoben."""
        if self.crit_low is not None and value < self.crit_low + margin:
            return "critical", f"< {self.crit_low:g}"
        if self.crit_high is not None and value > self.crit_high - margin:
            return "critical", f"> {self.crit_high:g}"
        if self.warn_low is not None and value < self.warn_low + margin:
            return "warning", f"< {self.warn_low:g}"
        if self.warn_high is not None and value > self.warn_high - margin:
            return "warning", f"> {self.warn_high:g}"
        return "ok", ""

    def validate(self) -> None:
        """Grenzen müssen in der Reihenfolge crit_low < warn_low < warn_high < crit_high liegen."""
        vals = self.defined()
        if any(b <= a for a, b in zip(vals, vals[1:])):
            raise ValueError("Limits must increase: crit low < warn low < warn high < crit high")


def default_limits(key: str) -> LimitSet:
    p = PARAMETERS_BY_KEY[key]
    return LimitSet(p.crit_low, p.warn_low, p.warn_high, p.crit_high)


def alarm_to_dict(a: Alarm) -> dict:
    p = PARAMETERS_BY_KEY.get(a.param_key)
    return {
        "id": a.id,
        "param_key": a.param_key,
        "param_label": p.label if p else a.param_key,
        "unit": p.unit if p else "",
        "decimals": p.decimals if p else 2,
        "severity": a.severity,
        "current": a.current,
        "active": a.cleared_at is None,
        "acknowledged": a.acknowledged_at is not None,
        "limit_text": a.limit_text,
        "value_at_raise": a.value_at_raise,
        "last_value": a.last_value,
        "raised_at": iso(a.raised_at),
        "cleared_at": iso_or_none(a.cleared_at),
        "acknowledged_at": iso_or_none(a.acknowledged_at),
        "acknowledged_by": a.acknowledged_by,
    }


class AlarmEngine:
    """Prüft jedes Telemetrie-Paket gegen die Grenzwerte und führt die Alarme."""

    def __init__(self) -> None:
        self.limits: dict[str, LimitSet] = {}
        self._state: dict[str, str] = {}  # aktuelle Stufe je Messwert
        self._open_ids: dict[str, int] = {}  # Messwert → Id des aktiven Alarms

    # ---------------------------------------------------------- Laden
    def load(self) -> None:
        """Grenzwerte aus der DB laden (fehlende mit Standardwerten anlegen)
        und noch aktive Alarme übernehmen (z. B. nach einem Neustart)."""
        with session_scope() as s:
            stored = {row.param_key: row for row in s.scalars(select(Limit))}
            for p in PARAMETERS:
                if p.key not in stored:
                    d = default_limits(p.key)
                    if d.is_empty():
                        continue
                    row = Limit(param_key=p.key, **asdict(d))
                    s.add(row)
                    stored[p.key] = row
            self.limits = {k: LimitSet(r.crit_low, r.warn_low, r.warn_high, r.crit_high, r.enabled)
                           for k, r in stored.items()}
            self._state, self._open_ids = {}, {}
            for a in s.scalars(select(Alarm).where(Alarm.cleared_at.is_(None))):
                self._state[a.param_key] = a.current
                self._open_ids[a.param_key] = a.id

    def reset(self) -> None:
        """Alle Alarme löschen (Demo-Reset). Grenzwerte bleiben erhalten."""
        with session_scope() as s:
            s.execute(delete(Alarm))
        self._state, self._open_ids = {}, {}

    # ------------------------------------------------------ Auswertung
    def process(self, frame: dict, t: datetime) -> list[dict]:
        """
        Prüft ein Paket. Ergänzt im Paket das Feld "limits" (Messwert → Stufe,
        nur verletzte Werte) und gibt alle Alarme zurück, die sich geändert haben.
        """
        changed: list[Alarm] = []
        status: dict[str, str] = {}
        values = frame["values"]

        keys = set(self.limits) | set(self._state)
        with session_scope() as s:
            for key in keys:
                if key not in values:
                    continue
                value = values[key]
                ls = self.limits.get(key)
                current = self._state.get(key, "ok")

                if ls is None or not ls.enabled or ls.is_empty():
                    new, text = "ok", ""
                else:
                    raw, text = ls.classify(value)
                    if RANK[raw] >= RANK[current]:
                        new = raw  # gleich oder schlechter: sofort übernehmen
                    else:
                        # besser: nur so weit herabstufen, wie das Totband erlaubt
                        relaxed, _ = ls.classify(value, margin=ls.deadband())
                        new = max(raw, min(current, relaxed, key=RANK.get), key=RANK.get)
                        if new != raw:
                            text = ls.classify(value, margin=ls.deadband())[1]

                if new != "ok":
                    status[key] = new
                if new == current:
                    continue
                self._state[key] = new
                changed.append(self._transition(s, key, current, new, value, text, t))
            s.flush()
            result = [alarm_to_dict(a) for a in changed]

        frame["limits"] = status
        return result

    def _transition(self, s, key: str, old: str, new: str, value: float, text: str,
                    t: datetime) -> Alarm:
        """Legt einen Alarm an, stuft ihn um oder beendet ihn."""
        unit = PARAMETERS_BY_KEY[key].unit
        if old == "ok":
            alarm = Alarm(param_key=key, severity=new, current=new, limit_text=f"{text} {unit}",
                          value_at_raise=value, last_value=value, raised_at=t)
            s.add(alarm)
            s.flush()  # vergibt die Id
            self._open_ids[key] = alarm.id
            return alarm

        alarm = s.get(Alarm, self._open_ids[key])
        alarm.current = new
        alarm.last_value = value
        if new == "ok":
            alarm.cleared_at = t
            self._open_ids.pop(key, None)
            self._state.pop(key, None)
        elif RANK[new] > RANK[alarm.severity]:
            # Eskalation von Warnung zu kritisch: muss erneut bestätigt werden
            alarm.severity = new
            alarm.limit_text = f"{text} {unit}"
            alarm.acknowledged_at = None
            alarm.acknowledged_by = None
        return alarm

    # ----------------------------------------------------- Bestätigen
    def acknowledge(self, alarm_ids: list[int] | None, user: str, t: datetime) -> list[dict]:
        """Bestätigt die angegebenen Alarme (None = alle unbestätigten)."""
        with session_scope() as s:
            query = select(Alarm).where(Alarm.acknowledged_at.is_(None))
            if alarm_ids is not None:
                query = query.where(Alarm.id.in_(alarm_ids))
            alarms = list(s.scalars(query))
            for a in alarms:
                a.acknowledged_at = t
                a.acknowledged_by = user
            s.flush()
            return [alarm_to_dict(a) for a in alarms]

    # ---------------------------------------------------------- Abfragen
    @staticmethod
    def list_open() -> list[dict]:
        """Alle Alarme, die noch Aufmerksamkeit brauchen (aktiv oder unbestätigt)."""
        with session_scope() as s:
            query = (select(Alarm)
                     .where((Alarm.cleared_at.is_(None)) | (Alarm.acknowledged_at.is_(None)))
                     .order_by(Alarm.raised_at.desc()))
            return [alarm_to_dict(a) for a in s.scalars(query)]

    @staticmethod
    def list_history(limit: int = 100) -> list[dict]:
        """Erledigte Alarme (abgeklungen und bestätigt), neueste zuerst."""
        with session_scope() as s:
            query = (select(Alarm)
                     .where(Alarm.cleared_at.is_not(None), Alarm.acknowledged_at.is_not(None))
                     .order_by(Alarm.raised_at.desc()).limit(limit))
            return [alarm_to_dict(a) for a in s.scalars(query)]

    # ------------------------------------------------------- Grenzwerte
    def limits_catalog(self) -> list[dict]:
        with session_scope() as s:
            rows = {r.param_key: r for r in s.scalars(select(Limit))}
        out = []
        for p in PARAMETERS:
            row = rows.get(p.key)
            ls = self.limits.get(p.key, LimitSet())
            out.append({
                "param_key": p.key,
                **asdict(ls),
                "default": asdict(default_limits(p.key)),
                "updated_by": row.updated_by if row else None,
                "updated_at": iso_or_none(row.updated_at) if row else None,
            })
        return out

    def update_limits(self, key: str, new: LimitSet, user: str, t: datetime) -> None:
        if key not in PARAMETERS_BY_KEY:
            raise KeyError(key)
        new.validate()
        with session_scope() as s:
            row = s.get(Limit, key) or Limit(param_key=key)
            row.crit_low, row.warn_low = new.crit_low, new.warn_low
            row.warn_high, row.crit_high = new.warn_high, new.crit_high
            row.enabled, row.updated_by, row.updated_at = new.enabled, user, t
            s.merge(row)
        self.limits[key] = new
