"""
Sonnenstand und Erdschatten.

Ein Satellit in niedriger Erdumlaufbahn (LEO) fliegt etwa alle 95 Minuten um
die Erde und verbringt davon bis zu ~35 Minuten im Erdschatten ("Eklipse").
In der Eklipse liefern die Solarzellen keinen Strom, die Batterie entlädt sich,
und der Satellit kühlt ab.

Für die Sonnenposition nutzen wir die Näherungsformel aus dem "Astronomical
Almanac" (Genauigkeit ~0,01°). Das reicht völlig und spart uns die 17 MB große
Ephemeriden-Datei, die Skyfield sonst herunterladen müsste.
"""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np

AU_KM = 149_597_870.7  # Astronomische Einheit (mittlerer Abstand Erde–Sonne)
R_EARTH_KM = 6378.137
R_SUN_KM = 696_000.0


def sun_position_km(t: datetime) -> np.ndarray:
    """Position der Sonne relativ zum Erdmittelpunkt (äquatoriale Koordinaten, km)."""
    # Tage seit der Standardepoche J2000.0 (1. Jan. 2000, 12:00 TT)
    jd = t.timestamp() / 86400.0 + 2440587.5
    n = jd - 2451545.0
    mean_lon = math.radians((280.460 + 0.9856474 * n) % 360)  # mittlere Länge
    g = math.radians((357.528 + 0.9856003 * n) % 360)  # mittlere Anomalie
    ecl_lon = mean_lon + math.radians(1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    obliquity = math.radians(23.439 - 0.0000004 * n)  # Schiefe der Ekliptik
    dist = (1.00014 - 0.01671 * math.cos(g) - 0.00014 * math.cos(2 * g)) * AU_KM
    return dist * np.array([
        math.cos(ecl_lon),
        math.cos(obliquity) * math.sin(ecl_lon),
        math.sin(obliquity) * math.sin(ecl_lon),
    ])


def sunlit_fraction(sat_km: np.ndarray, sun_km: np.ndarray) -> float:
    """
    Anteil der Sonnenscheibe, den der Satellit sieht: 1 = volle Sonne,
    0 = Kernschatten (Umbra), dazwischen = Halbschatten (Penumbra).

    Methode (Montenbruck & Gill, "Satellite Orbits", Kap. 3.4): Wir vergleichen
    vom Satelliten aus gesehen die scheinbare Größe von Sonne und Erde und ihren
    Winkelabstand. Überlappen sich die Scheiben, ist der Satellit (teilweise)
    im Schatten.
    """
    to_sun = sun_km - sat_km
    d_sat = np.linalg.norm(sat_km)
    d_sun = np.linalg.norm(to_sun)
    a = math.asin(R_SUN_KM / d_sun)  # scheinbarer Radius der Sonne
    b = math.asin(min(1.0, R_EARTH_KM / d_sat))  # scheinbarer Radius der Erde
    cos_c = float(np.dot(-sat_km, to_sun) / (d_sat * d_sun))
    c = math.acos(max(-1.0, min(1.0, cos_c)))  # Winkelabstand Erde–Sonne

    if c >= a + b:
        return 1.0  # Scheiben berühren sich nicht → volle Sonne
    if c <= b - a:
        return 0.0  # Sonne komplett hinter der Erde → Kernschatten
    # Teilweise Überdeckung: Fläche der Überlappung zweier Kreise
    x = (c * c + a * a - b * b) / (2 * c)
    y = math.sqrt(max(0.0, a * a - x * x))
    overlap = a * a * math.acos(max(-1.0, min(1.0, x / a))) \
        + b * b * math.acos(max(-1.0, min(1.0, (c - x) / b))) - c * y
    return max(0.0, min(1.0, 1.0 - overlap / (math.pi * a * a)))
