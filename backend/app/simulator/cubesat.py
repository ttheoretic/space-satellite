"""
Physikalisch motivierter Simulator eines 6U-CubeSats.

Das Modell ist bewusst einfach, aber die Zusammenhänge stimmen:

    echte Bahn (TLE) ──► Sonne oder Erdschatten?
                              │
            ┌─────────────────┼────────────────────┐
            ▼                 ▼                    ▼
     Solarleistung      Temperaturen          (Lage beeinflusst
            │           folgen träge            die Solarleistung)
            ▼
     Batterie lädt / entlädt ──► Spannung, Strom, Ladezustand

Fachbegriffe:
  EPS   – Electrical Power System (Energieversorgung)
  ADCS  – Attitude Determination and Control System (Lageregelung)
  FDIR  – Fault Detection, Isolation and Recovery: Bordsoftware, die Fehler
          selbst erkennt und den Satelliten in einen sicheren Zustand bringt
  SAFE  – Sicherheitsmodus: Nutzlast aus, Satellit richtet sich grob zur Sonne
          aus und wartet auf Anweisungen vom Boden
"""

from __future__ import annotations

import math
import random
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
from skyfield.api import EarthSatellite, wgs84

from ..clock import iso
from ..orbit.tle import ts
from ..parameters import PARAMETERS
from .faults import FAULT_TYPES, FAULT_TYPES_BY_KEY
from .sun import sun_position_km, sunlit_fraction

# --- Konstanten des Modells ------------------------------------------------
MAX_SUBSTEP_S = 10.0  # Rechenschritt; bei Zeitraffer wird in Teilschritte zerlegt
BATTERY_CAPACITY_WH = 40.0
BATTERY_R_INTERNAL = 0.15  # Innenwiderstand in Ohm
SOLAR_PEAK_W = 20.0  # Solarleistung bei voller Sonne und perfekter Ausrichtung

# Leerlaufspannung (OCV) einer 2S-Li-Ionen-Batterie abhängig vom Ladezustand
_SOC_POINTS = [0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0]
_OCV_POINTS = [6.0, 6.8, 7.0, 7.3, 7.6, 7.9, 8.05, 8.3]

# Verbraucher in Watt
P_BUS = 3.0  # Bordcomputer, Funk-Empfänger, Sensoren – immer an
P_PAYLOAD = 3.5  # Nutzlast, nur im NOMINAL-Modus
P_ADCS = 1.2  # Lageregelung im Normalbetrieb
P_ADCS_FAULT = 2.5  # Reaktionsräder drehen bei Störung hoch
P_HEATER = 2.5
P_LATCHUP = 7.0  # zusätzlicher Kurzschlussstrom bei Latch-up

FDIR_SAFE_SOC = 0.30  # unter 30 % Ladezustand → automatisch SAFE


def _approach(value: float, target: float, dt: float, tau: float) -> float:
    """Exponentielle Annäherung an einen Zielwert (Zeitkonstante tau in s).
    So verhalten sich z. B. Temperaturen: erst schnell, dann immer langsamer."""
    return target + (value - target) * math.exp(-dt / tau)


def _wrap180(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


@dataclass
class SpacecraftState:
    """Der innere Zustand des Satelliten (was wirklich 'an Bord' passiert)."""

    mode: str = "NOMINAL"  # NOMINAL | SAFE
    soc: float = 0.85  # Ladezustand 0..1
    battery_temp: float = 8.0
    obc_temp: float = 28.0
    panel_temp: float = 20.0
    heater_mode: str = "AUTO"  # AUTO (Thermostat) | ON | OFF
    heater_on: bool = False
    pointing_error: float = 0.4
    angular_rate: float = 0.06
    attitude_phase: float = 0.0
    faults: set[str] = field(default_factory=set)
    # zuletzt berechnete abgeleitete Größen
    illumination: float = 1.0
    solar_power: float = 0.0
    consumption: float = 0.0
    battery_current: float = 0.0
    battery_voltage: float = 7.9


class CubeSatSimulator:
    def __init__(self, satellite_provider: Callable[[], EarthSatellite],
                 seed: int | None = None) -> None:
        # satellite_provider liefert die aktuelle Bahn (kann sich bei neuer TLE ändern)
        self._satellite = satellite_provider
        self.rng = random.Random(seed)
        self.state = SpacecraftState()
        self.random_faults_enabled = True
        self.events: deque[dict] = deque(maxlen=200)
        self._new_events: list[dict] = []
        self._last_t: datetime | None = None
        self.seq = 0

    # ------------------------------------------------------------------ API
    def step_to(self, t: datetime, random_faults: bool = True) -> dict:
        """Simuliert bis zum Zeitpunkt t und gibt ein Telemetrie-Paket zurück."""
        if self._last_t is None or t <= self._last_t:
            self._last_t = t - timedelta(seconds=1)
        total = (t - self._last_t).total_seconds()
        if total > 1800:  # z. B. nach langer Pause: nur die letzte halbe Stunde nachrechnen
            self._last_t = t - timedelta(seconds=1800)
            total = 1800.0
        n = max(1, math.ceil(total / MAX_SUBSTEP_S))
        h = total / n
        for i in range(1, n + 1):
            self._integrate(self._last_t + timedelta(seconds=h * i), h, random_faults)
        self._last_t = t
        self.seq += 1
        return self._frame(t)

    def add_event(self, level: str, text: str) -> None:
        """Ereignis von außen ins Bordprotokoll schreiben (z. B. Kontaktbeginn)."""
        self._event(level, text)

    def pop_new_events(self) -> list[dict]:
        """Ereignisse seit dem letzten Aufruf (für den Live-Versand)."""
        ev, self._new_events = self._new_events, []
        return ev

    def trigger_fault(self, key: str) -> None:
        if key not in FAULT_TYPES_BY_KEY:
            raise KeyError(key)
        self._activate_fault(key, manual=True)

    def clear_faults(self) -> None:
        for key in list(self.state.faults):
            self.state.faults.discard(key)
            self._event("info", f"Fault cleared: {FAULT_TYPES_BY_KEY[key].label}")

    # Die folgenden Methoden sind die "Befehle", die der Satellit versteht.
    # Ab Schritt 4 werden sie über die Befehlsliste ausgelöst.
    def set_mode(self, mode: str) -> None:
        if mode not in ("NOMINAL", "SAFE"):
            raise ValueError(mode)
        if mode != self.state.mode:
            self.state.mode = mode
            self._event("info", f"Mode changed to {mode}")

    def set_heater_mode(self, mode: str) -> None:
        if mode not in ("AUTO", "ON", "OFF"):
            raise ValueError(mode)
        self.state.heater_mode = mode
        self._event("info", f"Battery heater set to {mode}")

    def reset_adcs(self) -> None:
        if "adcs_fault" in self.state.faults:
            self.state.faults.discard("adcs_fault")
            self._event("info", "ADCS reset – reaction wheels nominal, detumbling")
        else:
            self._event("info", "ADCS reset – no fault present")

    def send_command(self, code: str, args: dict) -> str:
        """Führt einen (simuliert gefunkten) Befehl aus und liefert die Antwort
        des Satelliten. Die Befehle sind in app/commands.py beschrieben."""
        if code == "PING":
            self._event("info", "PONG – spacecraft alive")
            return "PONG received"
        if code == "SET_MODE":
            self.set_mode(args["mode"])
            return f"ACK – mode is now {self.state.mode}"
        if code == "HEATER_MODE":
            self.set_heater_mode(args["mode"])
            return f"ACK – battery heater {args['mode']}"
        if code == "RESET_ADCS":
            had_fault = "adcs_fault" in self.state.faults
            self.reset_adcs()
            return "ACK – ADCS restarted, detumbling" if had_fault else "ACK – ADCS restarted"
        raise ValueError(f"Unknown command {code}")

    # ----------------------------------------------------------- Physik
    def _integrate(self, t: datetime, dt: float, random_faults: bool) -> None:
        s = self.state

        # 1) Bahn: Wo ist der Satellit, und sieht er die Sonne?
        geo = self._satellite().at(ts.from_datetime(t))
        sat_km = np.asarray(geo.position.km)
        illum = sunlit_fraction(sat_km, sun_position_km(t))
        if illum < 0.5 <= s.illumination:
            self._event("info", "Entering eclipse")
        elif s.illumination < 0.5 <= illum:
            self._event("info", "Leaving eclipse – sunlight")
        s.illumination = illum
        self._last_geo = geo

        # 2) Zufällige Fehler (Poisson-Prozess: Wahrscheinlichkeit ∝ Zeitschritt)
        if random_faults and self.random_faults_enabled:
            for ft in FAULT_TYPES:
                if ft.key not in s.faults and self.rng.random() < ft.rate_per_hour * dt / 3600:
                    self._activate_fault(ft.key, manual=False)

        # 3) Lageregelung (ADCS)
        if "adcs_fault" in s.faults:
            rate_target, err_target, tau = 3.0, 90.0, 180.0  # taumeln
        elif s.mode == "SAFE":
            rate_target, err_target, tau = 0.10, 3.0, 300.0  # grob zur Sonne
        else:
            rate_target, err_target, tau = 0.06, 0.4, 300.0  # fein ausgerichtet
        s.angular_rate = _approach(s.angular_rate, rate_target, dt, tau)
        s.pointing_error = _approach(s.pointing_error, err_target, dt, tau)
        s.attitude_phase = (s.attitude_phase + s.angular_rate * dt) % 360.0
        # Wie gut zeigen die Solarzellen zur Sonne? (taumelnd: im Mittel ~40 %)
        pointing_factor = max(math.cos(math.radians(s.pointing_error)),
                              0.4 + 0.15 * math.sin(math.radians(s.attitude_phase * 3)))

        # 4) Heizung: Thermostat schaltet mit Hysterese bei 3 °C ein und 7 °C aus
        if s.heater_mode == "ON":
            s.heater_on = True
        elif s.heater_mode == "OFF" or "heater_failure" in s.faults:
            s.heater_on = False
        elif s.battery_temp < 3.0:
            s.heater_on = True
        elif s.battery_temp > 7.0:
            s.heater_on = False

        # 5) Energiebilanz (EPS)
        payload_on = s.mode == "NOMINAL"
        if "payload_latchup" in s.faults and not payload_on:
            s.faults.discard("payload_latchup")
            self._event("info", "Payload powered off – latch-up cleared")
        s.consumption = (P_BUS
                         + (P_PAYLOAD if payload_on else 0.0)
                         + (P_ADCS_FAULT if "adcs_fault" in s.faults else P_ADCS)
                         + (P_HEATER if s.heater_on else 0.0)
                         + (P_LATCHUP if "payload_latchup" in s.faults else 0.0))
        # Heiße Solarzellen sind etwas weniger effizient (−0,4 % pro °C über 25 °C)
        efficiency = 1.0 - 0.004 * (s.panel_temp - 25.0)
        s.solar_power = max(0.0, SOLAR_PEAK_W * illum * pointing_factor * efficiency)

        net = s.solar_power - s.consumption
        if net > 0:
            # Laderegler: kurz vor "voll" wird der Ladestrom reduziert, Überschuss
            # verheizt. Unter 0 °C darf eine Li-Ionen-Zelle gar nicht laden.
            taper = 1.0 if s.soc < 0.9 else max(0.0, (1.0 - s.soc) / 0.1)
            if s.battery_temp < 0.0:
                taper = 0.0
            battery_power = net * taper * 0.95
        else:
            battery_power = net
        s.soc = min(1.0, max(0.02, s.soc + battery_power * dt / 3600 / BATTERY_CAPACITY_WH))
        ocv = float(np.interp(s.soc, _SOC_POINTS, _OCV_POINTS))
        s.battery_current = battery_power / ocv
        s.battery_voltage = ocv + s.battery_current * BATTERY_R_INTERNAL

        # 6) Temperaturen: jede nähert sich träge ihrem Gleichgewichtswert
        s.panel_temp = _approach(s.panel_temp, -40.0 + 115.0 * illum, dt, 900.0)
        batt_eq = -20.0 * (1 - illum) + 12.0 * illum + (25.0 if s.heater_on else 0.0)
        s.battery_temp = _approach(s.battery_temp, batt_eq, dt, 2400.0)
        obc_eq = 15.0 + 1.5 * s.consumption + 8.0 * illum
        s.obc_temp = _approach(s.obc_temp, obc_eq, dt, 1200.0)

        # 7) FDIR: Bordsoftware schützt die Batterie selbstständig
        if s.mode == "NOMINAL" and s.soc < FDIR_SAFE_SOC:
            s.mode = "SAFE"
            self._event("warning", "FDIR: battery low – autonomous switch to SAFE mode")

    # ------------------------------------------------------- Hilfsfunktionen
    def _activate_fault(self, key: str, manual: bool) -> None:
        if key == "payload_latchup" and self.state.mode != "NOMINAL":
            # Ohne eingeschaltete Nutzlast kein Latch-up möglich
            if manual:
                self._event("info", "Latch-up not possible: payload is off (SAFE mode)")
            return
        if key in self.state.faults:
            return
        self.state.faults.add(key)
        how = "triggered manually" if manual else "occurred"
        self._event("warning", f"Fault {how}: {FAULT_TYPES_BY_KEY[key].label}")

    def _event(self, level: str, text: str) -> None:
        t = iso(self._last_t) if self._last_t else None
        ev = {"t": t, "level": level, "text": text}
        self.events.append(ev)
        self._new_events.append(ev)

    def _frame(self, t: datetime) -> dict:
        """Baut das Telemetrie-Paket – so, wie es über Funk ankäme."""
        s = self.state
        sub = wgs84.geographic_position_of(self._last_geo)
        r = self.rng.gauss
        # Euler-Winkel nur zur Anzeige: kleine Schwingung bzw. Taumeln
        phase_rad = math.radians(s.attitude_phase)
        tumbling = s.angular_rate > 1.0
        values = {
            "battery_voltage": s.battery_voltage + r(0, 0.004),
            "battery_soc": s.soc * 100,
            "battery_current": s.battery_current + r(0, 0.01),
            "solar_power": max(0.0, s.solar_power + r(0, 0.05)),
            "power_consumption": s.consumption + r(0, 0.05),
            "battery_temp": s.battery_temp + r(0, 0.08),
            "obc_temp": s.obc_temp + r(0, 0.08),
            "panel_temp": s.panel_temp + r(0, 0.2),
            "pointing_error": abs(s.pointing_error + r(0, 0.02)),
            "angular_rate": abs(s.angular_rate + r(0, 0.003)),
            "roll": _wrap180(s.attitude_phase * 1.7) if tumbling
            else s.pointing_error * math.cos(phase_rad),
            "pitch": _wrap180(s.attitude_phase * 0.9) if tumbling
            else s.pointing_error * math.sin(phase_rad),
            "yaw": _wrap180(s.attitude_phase) if tumbling
            else 0.5 * s.pointing_error * math.sin(2 * phase_rad),
        }
        values = {p.key: round(values[p.key], p.decimals + 1) for p in PARAMETERS}
        return {
            "seq": self.seq,
            "t": iso(t),
            "mode": s.mode,
            "eclipse": s.illumination < 0.5,
            "illumination": round(s.illumination, 3),
            "heater_on": s.heater_on,
            "heater_mode": s.heater_mode,
            "faults": sorted(s.faults),
            "position": {
                "lat": round(float(sub.latitude.degrees), 3),
                "lon": round(float(sub.longitude.degrees), 3),
                "alt_km": round(float(sub.elevation.km), 1),
            },
            "values": values,
        }
