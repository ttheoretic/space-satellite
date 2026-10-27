"""
Fehlerbilder des simulierten CubeSats.

Jeder Fehler beschreibt eine typische Störung aus dem echten CubeSat-Betrieb:

  heater_failure   – Der Thermostat der Batterieheizung fällt aus. In der
                     Eklipse kühlt die Batterie unter 0 °C ab.
  payload_latchup  – Ein energiereiches Teilchen (kosmische Strahlung) löst in
                     der Nutzlast-Elektronik einen Kurzschluss aus ("Single
                     Event Latch-up"). Sie zieht plötzlich viel Strom.
  adcs_fault       – Ein Reaktionsrad (Schwungrad zur Lageregelung) spinnt.
                     Der Satellit taumelt, die Solarzellen verlieren die Sonne.

Fehler treten zufällig auf (wenn aktiviert) oder lassen sich über die
Oberfläche gezielt auslösen, damit man in einer Demo nicht auf den Zufall
warten muss. Die Texte erscheinen in der Oberfläche und sind daher Englisch.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FaultType:
    key: str
    label: str
    description: str
    recovery: str  # Wie man den Fehler behebt (wird in der Oberfläche angezeigt)
    rate_per_hour: float  # mittlere Häufigkeit pro Stunde Missionszeit


FAULT_TYPES: list[FaultType] = [
    FaultType(
        "heater_failure",
        "Battery heater thermostat failure",
        "The battery heater thermostat fails. In eclipse the battery cools below 0 °C.",
        "Switch the heater on manually (HEATER_MODE ON uses the backup circuit).",
        0.06,
    ),
    FaultType(
        "payload_latchup",
        "Payload single-event latch-up",
        "A high-energy particle triggers a short circuit in the payload electronics. "
        "Power draw jumps and the battery drains.",
        "Power the payload off with SET_MODE SAFE. Below 30 % state of charge the "
        "onboard FDIR switches to SAFE by itself.",
        0.06,
    ),
    FaultType(
        "adcs_fault",
        "Reaction wheel anomaly",
        "A reaction wheel misbehaves. The spacecraft starts tumbling and the solar "
        "arrays lose the sun.",
        "Restart attitude control with RESET_ADCS.",
        0.06,
    ),
]

FAULT_TYPES_BY_KEY = {f.key: f for f in FAULT_TYPES}


def fault_catalog() -> list[dict]:
    return [asdict(f) for f in FAULT_TYPES]
