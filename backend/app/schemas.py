"""
Pydantic-Modelle: beschreiben, wie Anfragen an die API aussehen müssen.
FastAPI prüft eingehende Daten automatisch dagegen und erzeugt daraus die
interaktive API-Dokumentation unter /docs.
"""

from __future__ import annotations

from pydantic import BaseModel


class SpeedRequest(BaseModel):
    speed: int


class LimitUpdate(BaseModel):
    """Neue Grenzwerte für einen Messwert. None = keine Grenze in dieser Richtung."""

    crit_low: float | None = None
    warn_low: float | None = None
    warn_high: float | None = None
    crit_high: float | None = None
    enabled: bool = True


class AckRequest(BaseModel):
    """Alarme bestätigen. ids weglassen = alle unbestätigten Alarme."""

    ids: list[int] | None = None


class ToggleRequest(BaseModel):
    enabled: bool


class StationUpdate(BaseModel):
    """Bodenstation: Name, Position (Grad), Höhe (m) und Mindestelevation (Grad)."""

    name: str
    lat: float
    lon: float
    alt_m: float = 0.0
    min_elevation: float = 5.0
