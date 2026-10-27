"""
Missionsuhr mit Zeitraffer.

Alle Programmteile (Simulator, Bahnberechnung, später Überflüge und Befehle)
fragen die Zeit hier ab statt direkt die Systemuhr. So können wir die
Simulation beschleunigen, ohne dass Bahnposition, Tag/Nacht und Überflüge
auseinanderlaufen.

Prinzip: Wir merken uns einen "Anker" – ein Paar aus echter Zeit und
Missionszeit. Die aktuelle Missionszeit ist dann
    missionszeit = anker_mission + (jetzt_echt - anker_echt) * faktor
Beim Ändern des Faktors setzen wir einfach einen neuen Anker.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone


class MissionClock:
    def __init__(self, start: datetime | None = None, speed: int = 1) -> None:
        self._anchor_real = time.monotonic()
        self._anchor_mission = start or datetime.now(timezone.utc)
        self._speed = speed

    @property
    def speed(self) -> int:
        return self._speed

    def now(self) -> datetime:
        """Aktuelle Missionszeit (immer UTC)."""
        elapsed = time.monotonic() - self._anchor_real
        return self._anchor_mission + timedelta(seconds=elapsed * self._speed)

    def set_speed(self, speed: int) -> None:
        """Zeitraffer-Faktor ändern, ohne dass die Missionszeit springt."""
        self._rebase(self.now())
        self._speed = speed

    def jump_to(self, t: datetime) -> None:
        """Missionszeit auf einen Zeitpunkt setzen (z. B. 'vorspulen')."""
        self._rebase(t)

    def offset_seconds(self) -> float:
        """Abstand Missionszeit − echte Zeit in Sekunden (zum Speichern)."""
        return (self.now() - datetime.now(timezone.utc)).total_seconds()

    def _rebase(self, mission_time: datetime) -> None:
        self._anchor_real = time.monotonic()
        self._anchor_mission = mission_time


def as_utc(t: datetime) -> datetime:
    """SQLite liefert Zeiten ohne Zeitzone zurück. Wir speichern immer UTC,
    also hängen wir die Zeitzone wieder an (sonst würde die Ortszeit angenommen)."""
    return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)


def iso(t: datetime) -> str:
    """ISO-8601-Zeitstempel mit Millisekunden – von allen Browsern sicher lesbar."""
    return as_utc(t).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def iso_or_none(t: datetime | None) -> str | None:
    return iso(t) if t else None


def parse_iso(s: str) -> datetime:
    """Gegenstück zu iso(). (Python 3.10 versteht das 'Z' am Ende noch nicht.)"""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
