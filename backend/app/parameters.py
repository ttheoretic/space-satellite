"""
Katalog der Telemetrie-Messwerte ("Parameter").

Hier steht an einer Stelle, welche Messwerte es gibt, wie sie heißen, welche
Einheit sie haben und welche Grenzwerte standardmäßig gelten. Das Frontend
liest diesen Katalog über die API und baut daraus die Anzeige auf.

Grenzwerte (ab Schritt 2 im Leitstand einstellbar):
  warn_*  – gelber Bereich: Aufmerksamkeit nötig
  crit_*  – roter Bereich: sofort handeln
  None    – für diese Richtung gibt es keine Grenze

Die Texte (label, description) erscheinen in der Oberfläche und sind daher Englisch.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str
    unit: str
    group: str  # Subsystem: power, thermal, attitude
    decimals: int
    description: str
    crit_low: float | None = None
    warn_low: float | None = None
    warn_high: float | None = None
    crit_high: float | None = None


PARAMETERS: list[Parameter] = [
    # --- EPS (Electrical Power System, Energieversorgung) -----------------
    Parameter("battery_voltage", "Battery Voltage", "V", "power", 2,
              "Terminal voltage of the 2S Li-ion battery (2 cells in series, 6.0–8.4 V)",
              crit_low=6.6, warn_low=7.0, warn_high=8.35, crit_high=8.45),
    Parameter("battery_soc", "State of Charge", "%", "power", 1,
              "Battery state of charge",
              crit_low=25, warn_low=40),
    Parameter("battery_current", "Battery Current", "A", "power", 2,
              "Battery current: positive = charging, negative = discharging",
              crit_low=-3.5, warn_low=-2.5, warn_high=2.5, crit_high=3.5),
    Parameter("solar_power", "Solar Power", "W", "power", 1,
              "Power delivered by the solar arrays (0 W in eclipse)"),
    Parameter("power_consumption", "Power Draw", "W", "power", 1,
              "Total power drawn by all onboard loads",
              warn_high=12, crit_high=14),
    # --- Thermal ----------------------------------------------------------
    Parameter("battery_temp", "Battery Temp", "°C", "thermal", 1,
              "Battery temperature. Li-ion cells must not be charged below 0 °C",
              crit_low=-5, warn_low=0, warn_high=40, crit_high=45),
    Parameter("obc_temp", "OBC Temp", "°C", "thermal", 1,
              "On-board computer temperature",
              crit_low=-20, warn_low=-10, warn_high=50, crit_high=60),
    Parameter("panel_temp", "Solar Panel Temp", "°C", "thermal", 1,
              "Temperature of an external solar panel",
              crit_low=-60, warn_low=-45, warn_high=85, crit_high=100),
    # --- ADCS (Attitude Determination and Control System, Lageregelung) ----
    Parameter("pointing_error", "Pointing Error", "°", "attitude", 2,
              "Angle between actual and commanded attitude",
              warn_high=5, crit_high=15),
    Parameter("angular_rate", "Angular Rate", "°/s", "attitude", 3,
              "Body rotation rate. High values mean the spacecraft is tumbling",
              warn_high=0.5, crit_high=2.0),
    Parameter("roll", "Roll", "°", "attitude", 1, "Rotation about the velocity axis"),
    Parameter("pitch", "Pitch", "°", "attitude", 1, "Rotation about the orbit-normal axis"),
    Parameter("yaw", "Yaw", "°", "attitude", 1, "Rotation about the nadir axis"),
]

PARAMETERS_BY_KEY = {p.key: p for p in PARAMETERS}


def parameter_catalog() -> list[dict]:
    return [asdict(p) for p in PARAMETERS]
