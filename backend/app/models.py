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

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
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


class Limit(Base):
    """Eingestellte Grenzwerte eines Messwerts (überschreibt die Standardwerte)."""

    __tablename__ = "limits"

    param_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    crit_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    warn_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    warn_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    crit_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Alarm(Base):
    """
    Ein Alarm entsteht, wenn ein Messwert eine Grenze verletzt.

    Lebenslauf eines Alarms (wie in echten Leitständen):
      aktiv & unbestätigt → jemand muss hinsehen
      aktiv & bestätigt   → bekannt, wird bearbeitet
      abgeklungen & unbestätigt → Wert ist wieder gut, aber noch niemand hat es gesehen
      abgeklungen & bestätigt   → erledigt, wandert ins Archiv
    """

    __tablename__ = "alarms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    param_key: Mapped[str] = mapped_column(String(64), index=True)
    # höchste erreichte Stufe ("warning" | "critical") und aktuelle Stufe ("ok" | …)
    severity: Mapped[str] = mapped_column(String(16))
    current: Mapped[str] = mapped_column(String(16))
    limit_text: Mapped[str] = mapped_column(String(64))  # z. B. "< 0.0 °C"
    value_at_raise: Mapped[float] = mapped_column(Float)
    last_value: Mapped[float] = mapped_column(Float)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(32), nullable=True)


class AuditEntry(Base):
    """Protokoll aller Bedienaktionen: wer hat wann was getan."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    real_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Command(Base):
    """
    Ein Befehl an den Satelliten und sein Weg durch den Freigabeprozess:

      awaiting_approval → approved → sent
              │               │
              └→ rejected     └→ (cancelled)

    Die Freigabe bezieht sich auf den Inhalt (Befehl + Argumente). Der Inhalt
    lässt sich danach nicht mehr ändern – nur der Überflug, in dem gesendet wird.
    """

    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32))
    args: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    comment: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(24), index=True)
    # Zugewiesener Überflug (Kennung und Zeitfenster werden mitgespeichert)
    pass_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pass_aos: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pass_los: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[str | None] = mapped_column(String(500), nullable=True)
