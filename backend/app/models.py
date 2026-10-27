"""
Datenbanktabellen.

Telemetrie speichern wir als eine Zeile pro Paket mit den Messwerten als JSON.
Das ist für einen Prototyp einfach und flexibel (neue Messwerte brauchen keine
Tabellenänderung). Für große Datenmengen würde man später auf eine
TimescaleDB-"Hypertable" mit einer Zeile pro Messwert umsteigen.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class TelemetryFrame(Base):
    """Ein Telemetrie-Paket, wie es der Satellit zu einem Zeitpunkt sendet."""

    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Missionszeit (UTC) des Pakets
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # Vollständiges Paket als JSON (Messwerte, Modus, Position …)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)


class Setting(Base):
    """Einfacher Schlüssel-Wert-Speicher, z. B. für den Stand der Missionsuhr."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
