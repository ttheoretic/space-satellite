"""
Demo-Personen und Rollenrechte.

Im Prototyp gibt es kein Login: Die Oberfläche schickt bei jeder Anfrage im
Kopffeld ``X-OrbitDesk-User`` mit, welche Person ausgewählt ist. Das Backend
prüft dann, ob diese Person die Aktion ausführen darf.

Für das fertige Produkt wird nur ``current_user`` ausgetauscht (z. B. gegen
ein Login mit Passwort oder Firmen-Konto). Alle Rechteprüfungen bleiben gleich.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from fastapi import Depends, Header, HTTPException


@dataclass(frozen=True)
class User:
    id: str
    name: str
    role: str  # operator | flight_director | engineer
    role_label: str


USERS: dict[str, User] = {
    u.id: u
    for u in [
        User("anna", "Anna", "operator", "Operator"),
        User("ben", "Ben", "flight_director", "Flight Director"),
        User("clara", "Clara", "engineer", "Engineer"),
    ]
}

# Welche Rolle darf was? (Der Engineer darf nur lesen.)
PERMISSIONS: dict[str, set[str]] = {
    "operator": {"alarm.ack", "limits.edit", "command.create", "command.schedule", "command.send"},
    "flight_director": {"alarm.ack", "limits.edit", "command.create", "command.schedule",
                        "command.approve", "command.send"},
    "engineer": set(),
}


def can(user: User, action: str) -> bool:
    return action in PERMISSIONS.get(user.role, set())


def user_catalog() -> list[dict]:
    return [{**asdict(u), "permissions": sorted(PERMISSIONS[u.role])} for u in USERS.values()]


def current_user(x_orbitdesk_user: str | None = Header(default=None)) -> User:
    """FastAPI-Abhängigkeit: ermittelt die handelnde Person aus dem Kopffeld."""
    user = USERS.get(x_orbitdesk_user or "")
    if user is None:
        raise HTTPException(status_code=401, detail="Select a user first")
    return user


def require(action: str):
    """Erzeugt eine Abhängigkeit, die nur Personen mit diesem Recht durchlässt.

    Verwendung:  def endpoint(user: User = Depends(require("alarm.ack"))): …
    """

    def dependency(user: User = Depends(current_user)) -> User:
        if not can(user, action):
            raise HTTPException(status_code=403,
                                detail=f"{user.name} ({user.role_label}) may not do this")
        return user

    return dependency
