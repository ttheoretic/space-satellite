"""
Befehlskatalog und Freigabeprozess ("Commanding").

Im echten Betrieb ist ein falscher Befehl eines der größten Risiken: Er kann
den Satelliten im schlimmsten Fall verloren gehen lassen. Deshalb gilt:

  1. Ein Befehl wird angelegt (Operator oder Flight Director).
  2. Er wird einem Überflug zugewiesen – nur dann besteht Funkkontakt.
  3. Eine ZWEITE Person (Flight Director) prüft und gibt ihn frei
     ("Vier-Augen-Prinzip"). Wer ihn angelegt hat, darf ihn nicht freigeben.
  4. Während des Überflugs wird er gesendet. Der Satellit bestätigt ihn.
  5. Jeder Schritt steht mit Person und Zeit im Protokoll.

Das Senden ist simuliert: Der Befehl geht an die Telemetrie-Quelle (hier den
Simulator). Für eine echte Bodenstation wird dort später die Funkstrecke
angeschlossen; dieser Ablauf bleibt gleich.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

from sqlalchemy import select

from .clock import as_utc, iso, iso_or_none
from .db import session_scope
from .models import Command


@dataclass(frozen=True)
class CommandArg:
    name: str
    options: tuple[str, ...]


@dataclass(frozen=True)
class CommandDef:
    code: str
    label: str
    description: str
    args: tuple[CommandArg, ...] = field(default_factory=tuple)


# Die Texte erscheinen in der Oberfläche und sind daher Englisch.
CATALOG: list[CommandDef] = [
    CommandDef("PING", "Ping", "Connectivity check. The spacecraft answers with PONG."),
    CommandDef("SET_MODE", "Set operating mode",
               "NOMINAL: payload on, fine pointing. SAFE: payload off, coarse sun pointing, "
               "minimum power – used after anomalies.",
               (CommandArg("mode", ("NOMINAL", "SAFE")),)),
    CommandDef("HEATER_MODE", "Battery heater mode",
               "AUTO: thermostat. ON: force heater on via the backup circuit. OFF: heater off.",
               (CommandArg("mode", ("AUTO", "ON", "OFF")),)),
    CommandDef("RESET_ADCS", "Reset attitude control",
               "Restarts the attitude determination and control system (reaction wheels)."),
]
CATALOG_BY_CODE = {c.code: c for c in CATALOG}

# Zustände
AWAITING = "awaiting_approval"
APPROVED = "approved"
REJECTED = "rejected"
SENT = "sent"
CANCELLED = "cancelled"
FINAL = {REJECTED, SENT, CANCELLED}


class CommandError(ValueError):
    """Aktion ist im aktuellen Zustand nicht erlaubt (→ HTTP 409/400)."""


def catalog() -> list[dict]:
    return [asdict(c) for c in CATALOG]


def validate(code: str, args: dict) -> dict:
    """Prüft Befehl und Argumente gegen den Katalog und gibt saubere Argumente zurück."""
    cdef = CATALOG_BY_CODE.get(code)
    if cdef is None:
        raise CommandError(f"Unknown command {code}")
    clean = {}
    for arg in cdef.args:
        value = args.get(arg.name)
        if value not in arg.options:
            raise CommandError(f"{code}: argument '{arg.name}' must be one of {', '.join(arg.options)}")
        clean[arg.name] = value
    extra = set(args) - {a.name for a in cdef.args}
    if extra:
        raise CommandError(f"{code}: unexpected argument(s) {', '.join(sorted(extra))}")
    return clean


def text(code: str, args: dict) -> str:
    """Kurzform für Anzeige und Protokoll, z. B. 'HEATER_MODE ON'."""
    return " ".join([code, *[str(v) for v in args.values()]])


def to_dict(c: Command, now: datetime) -> dict:
    """Befehl für die Oberfläche, inklusive abgeleitetem Zustand des Überflugs."""
    pass_state = None
    if c.pass_aos and c.pass_los:
        aos, los = as_utc(c.pass_aos), as_utc(c.pass_los)
        pass_state = "upcoming" if now < aos else "in_progress" if now <= los else "over"
    return {
        "id": c.id,
        "code": c.code,
        "args": c.args,
        "text": text(c.code, c.args),
        "comment": c.comment,
        "status": c.status,
        "pass_id": c.pass_id,
        "pass_aos": iso_or_none(c.pass_aos),
        "pass_los": iso_or_none(c.pass_los),
        "pass_state": pass_state,
        "created_by": c.created_by,
        "created_at": iso(c.created_at),
        "decided_by": c.decided_by,
        "decided_at": iso_or_none(c.decided_at),
        "reject_reason": c.reject_reason,
        "sent_by": c.sent_by,
        "sent_at": iso_or_none(c.sent_at),
        "result": c.result,
    }


def list_all(now: datetime, limit: int = 200) -> list[dict]:
    with session_scope() as s:
        rows = s.scalars(select(Command).order_by(Command.id.desc()).limit(limit))
        return [to_dict(c, now) for c in rows]
