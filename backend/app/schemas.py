"""
Pydantic-Modelle: beschreiben, wie Anfragen an die API aussehen müssen.
FastAPI prüft eingehende Daten automatisch dagegen und erzeugt daraus die
interaktive API-Dokumentation unter /docs.
"""

from __future__ import annotations

from pydantic import BaseModel


class SpeedRequest(BaseModel):
    speed: int
