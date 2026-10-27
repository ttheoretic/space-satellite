"""
Schnittstelle "Telemetrie-Quelle".

Der Missionskern weiß nicht, woher die Telemetrie kommt – er kennt nur diese
Schnittstelle. Heute steckt der Simulator dahinter. Für das fertige Produkt
kommt eine zweite Quelle hinzu, die echte Pakete von einer Bodenstation
empfängt und entschlüsselt (z. B. AX.25/KISS oder CCSDS). Dashboard, Alarme
und Speicherung bleiben dabei unverändert.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class TelemetrySource(Protocol):
    def step_to(self, t: datetime, random_faults: bool = True) -> dict:
        """Liefert das Telemetrie-Paket für den Zeitpunkt t (siehe Format in
        simulator/cubesat.py: t, mode, values, position …)."""
        ...

    def pop_new_events(self) -> list[dict]:
        """Bordereignisse seit dem letzten Aufruf."""
        ...
