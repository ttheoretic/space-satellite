"""
Überflugberechnung ("Pass Prediction").

Ein Überflug ist die Zeitspanne, in der der Satellit von der Bodenstation aus
über dem Horizont steht und man mit ihm funken kann. Begriffe:

  AOS  – Acquisition of Signal: Satellit steigt über die Mindestelevation
  TCA  – Time of Closest Approach: höchster Punkt am Himmel
  LOS  – Loss of Signal: Satellit sinkt wieder unter die Mindestelevation

  Elevation – Winkel über dem Horizont (0° = Horizont, 90° = senkrecht oben)
  Azimut    – Himmelsrichtung (0° = Nord, 90° = Ost, 180° = Süd, 270° = West)

Die Mindestelevation (Standard 5°) berücksichtigt, dass Gebäude, Bäume und
Berge den Horizont verdecken und das Signal knapp über dem Horizont schwach ist.
Je höher die maximale Elevation, desto länger und besser der Überflug.

Die eigentliche Rechnung übernimmt Skyfield (find_events).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from skyfield.api import EarthSatellite, wgs84

from ..clock import iso
from .tle import ts


@dataclass(frozen=True)
class GroundStation:
    name: str
    lat: float  # Grad, Nord positiv
    lon: float  # Grad, Ost positiv
    alt_m: float  # Höhe über dem Meeresspiegel
    min_elevation: float = 5.0  # Grad

    def validate(self) -> None:
        if not -90 <= self.lat <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= self.lon <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        if not -500 <= self.alt_m <= 9000:
            raise ValueError("Altitude must be between -500 and 9000 m")
        if not 0 <= self.min_elevation <= 45:
            raise ValueError("Minimum elevation must be between 0 and 45°")
        if not self.name.strip():
            raise ValueError("Name must not be empty")

    def topos(self):
        return wgs84.latlon(self.lat, self.lon, elevation_m=self.alt_m)

    def to_dict(self) -> dict:
        return asdict(self)


def look_angles(sat: EarthSatellite, station: GroundStation, t: datetime) -> dict:
    """Wo steht der Satellit von der Station aus gesehen? (Elevation, Azimut, Entfernung)"""
    alt, az, dist = (sat - station.topos()).at(ts.from_datetime(t)).altaz()
    return {
        "elevation": round(float(alt.degrees), 2),
        "azimuth": round(float(az.degrees), 1),
        "range_km": round(float(dist.km), 1),
        "in_contact": float(alt.degrees) >= station.min_elevation,
    }


def pass_id(aos: datetime) -> str:
    """Stabile Kennung eines Überflugs aus seiner AOS-Zeit, z. B. 'P-20261027-1531'.
    (Ab Schritt 4 werden Befehle über diese Kennung einem Überflug zugeordnet.)"""
    return aos.strftime("P-%Y%m%d-%H%M")


def compute_passes(sat: EarthSatellite, station: GroundStation, start: datetime,
                   end: datetime) -> list[dict]:
    """Alle vollständigen Überflüge zwischen start und end."""
    topos = station.topos()
    diff = sat - topos
    times, events = sat.find_events(topos, ts.from_datetime(start), ts.from_datetime(end),
                                    altitude_degrees=station.min_elevation)
    passes: list[dict] = []
    current: dict | None = None
    for t, event in zip(times, events):
        if event == 0:  # Aufgang (AOS)
            current = {"aos_t": t, "tca_t": None, "max_el": -90.0}
        elif event == 1 and current is not None:  # Kulmination (TCA)
            el = diff.at(t).altaz()[0].degrees
            if el > current["max_el"]:
                current.update(tca_t=t, max_el=float(el))
        elif event == 2 and current is not None:  # Untergang (LOS)
            current["los_t"] = t
            passes.append(_finish(diff, current))
            current = None
    # Überflüge, die am Fensteranfang schon laufen oder am Ende noch nicht
    # vorbei sind, werden weggelassen – das Fenster wird dafür großzügig gewählt.
    return passes


def _finish(diff, p: dict) -> dict:
    aos, los = p["aos_t"].utc_datetime(), p["los_t"].utc_datetime()
    has_tca = p["tca_t"] is not None
    tca_t = p["tca_t"] if has_tca else ts.from_datetime(aos + (los - aos) / 2)
    el_max = p["max_el"] if has_tca else float(diff.at(tca_t).altaz()[0].degrees)
    az = lambda t: round(float(diff.at(t).altaz()[1].degrees), 1)  # noqa: E731
    return {
        "id": pass_id(aos),
        "aos": iso(aos),
        "tca": iso(tca_t.utc_datetime()),
        "los": iso(los),
        "duration_s": round((los - aos).total_seconds()),
        "max_elevation": round(el_max, 1),
        "aos_azimuth": az(p["aos_t"]),
        "tca_azimuth": az(tca_t),
        "los_azimuth": az(p["los_t"]),
    }


def pass_track(sat: EarthSatellite, station: GroundStation, aos: datetime, los: datetime,
               step_s: int = 10) -> list[dict]:
    """Bahn eines Überflugs am Himmel (Azimut/Elevation alle step_s Sekunden)
    – für die Himmelskarte ("Sky Plot") in der Oberfläche."""
    diff = sat - station.topos()
    points = []
    t = aos
    while t <= los + timedelta(seconds=step_s):
        alt, az, _ = diff.at(ts.from_datetime(min(t, los))).altaz()
        points.append({"t": iso(min(t, los)), "elevation": round(float(alt.degrees), 2),
                       "azimuth": round(float(az.degrees), 1)})
        if t >= los:
            break
        t += timedelta(seconds=step_s)
    return points


class PassPredictor:
    """Berechnet Überflüge und merkt sich das Ergebnis, bis sich Station,
    TLE oder die volle Stunde ändern (Neuberechnung dauert < 1 s)."""

    LOOKBACK = timedelta(minutes=30)
    EXTRA = timedelta(hours=6)

    def __init__(self) -> None:
        self._key: tuple | None = None
        self._passes: list[dict] = []

    def invalidate(self) -> None:
        self._key = None

    def get(self, sat: EarthSatellite, station: GroundStation, now: datetime,
            hours: float = 48) -> list[dict]:
        """Überflüge, die noch nicht vorbei sind und in den nächsten `hours` beginnen."""
        hour = now.replace(minute=0, second=0, microsecond=0)
        key = (sat.model.jdsatepoch, sat.model.jdsatepochF, station, hour, hours)
        if key != self._key:
            start = hour - self.LOOKBACK
            self._passes = compute_passes(sat, station, start,
                                          hour + timedelta(hours=hours) + self.EXTRA)
            self._key = key
        now_s, horizon = iso(now), iso(now + timedelta(hours=hours))
        # ISO-Zeitstempel im selben Format lassen sich direkt als Text vergleichen
        return [p for p in self._passes if p["los"] > now_s and p["aos"] < horizon]
