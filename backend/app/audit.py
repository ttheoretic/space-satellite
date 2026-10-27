"""
Protokoll der Bedienaktionen ("Audit-Log"): wer hat wann was getan.

Jede Aktion, die den Betrieb beeinflusst (Grenzwert ändern, Alarm bestätigen,
ab Schritt 4 auch Befehle), wird hier mit Person, Missionszeit und echter
Uhrzeit festgehalten. Einträge werden nie geändert oder gelöscht.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from .clock import iso
from .db import session_scope
from .models import AuditEntry


def record(user: str, action: str, mission_time: datetime, **details) -> dict:
    with session_scope() as s:
        entry = AuditEntry(mission_time=mission_time, real_time=datetime.now(timezone.utc),
                           user=user, action=action, details=details)
        s.add(entry)
        s.flush()
        return entry_to_dict(entry)


def entry_to_dict(e: AuditEntry) -> dict:
    return {"id": e.id, "mission_time": iso(e.mission_time), "real_time": iso(e.real_time),
            "user": e.user, "action": e.action, "details": e.details}


def recent(limit: int = 200) -> list[dict]:
    with session_scope() as s:
        rows = s.scalars(select(AuditEntry).order_by(AuditEntry.id.desc()).limit(limit))
        return [entry_to_dict(e) for e in rows]
