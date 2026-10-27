"""
Zentrale Einstellungen von OrbitDesk.

Alle Werte haben sinnvolle Standardwerte und lassen sich über
Umgebungsvariablen überschreiben (z. B. in docker-compose.yml oder in der Shell:
``ORBITDESK_NORAD_ID=12345 uvicorn app.main:app``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Basisverzeichnis des Backends (…/backend)
BACKEND_DIR = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    """Liest eine Umgebungsvariable mit dem Präfix ORBITDESK_."""
    return os.environ.get(f"ORBITDESK_{name}", default)


@dataclass(frozen=True)
class Settings:
    # --- Satellit ---------------------------------------------------------
    # NORAD-Katalognummer: die weltweit eindeutige Nummer eines Objekts im
    # Erdorbit. 59112 = SONATE-2 (Universität Würzburg, 6U-CubeSat).
    norad_id: int = int(_env("NORAD_ID", "59112"))
    satellite_name: str = _env("SATELLITE_NAME", "SONATE-2")

    # --- Bodenstation (Standard: TU Berlin) -------------------------------
    station_name: str = _env("STATION_NAME", "TU Berlin")
    station_lat_deg: float = float(_env("STATION_LAT", "52.51"))
    station_lon_deg: float = float(_env("STATION_LON", "13.33"))
    station_alt_m: float = float(_env("STATION_ALT", "60"))

    # --- TLE-Bahndaten ----------------------------------------------------
    # {norad} wird durch die NORAD-ID ersetzt.
    tle_url: str = _env(
        "TLE_URL", "https://celestrak.org/NORAD/elements/gp.php?CATNR={norad}&FORMAT=TLE"
    )
    # Wie oft (in echten Stunden) die TLE neu geladen wird.
    tle_refresh_hours: float = float(_env("TLE_REFRESH_HOURS", "6"))
    # Ab diesem Alter (Tage) wird in der Oberfläche gewarnt.
    tle_warn_age_days: float = float(_env("TLE_WARN_AGE_DAYS", "14"))
    # Auf False setzen, um nie ins Internet zu gehen (reiner Offline-Modus).
    tle_online: bool = _env("TLE_ONLINE", "true").lower() == "true"

    # --- Daten & Speicherung ---------------------------------------------
    data_dir: Path = Path(_env("DATA_DIR", str(BACKEND_DIR.parent / "data")))
    # SQLAlchemy-Verbindungs-URL. Leer = SQLite-Datei im data_dir.
    # Später z. B.: postgresql+psycopg://user:pw@host/orbitdesk
    database_url: str = _env("DATABASE_URL", "")
    # Wie lange Telemetrie aufbewahrt wird (in Stunden Missionszeit).
    retention_hours: float = float(_env("RETENTION_HOURS", "24"))

    # --- Simulator --------------------------------------------------------
    # Ein Telemetrie-Paket pro echter Sekunde.
    tick_seconds: float = float(_env("TICK_SECONDS", "1.0"))
    # Erlaubte Zeitraffer-Faktoren.
    speed_options: tuple[int, ...] = field(default=(1, 10, 60))
    # Beim allerersten Start wird so viel Vergangenheit "vorsimuliert",
    # damit die Diagramme sofort Kurven zeigen (in Stunden).
    backfill_hours: float = float(_env("BACKFILL_HOURS", "3"))

    # --- Frontend ---------------------------------------------------------
    # Ordner mit dem gebauten Frontend (npm run build). Existiert er,
    # liefert das Backend die Oberfläche direkt mit aus.
    static_dir: Path = Path(_env("STATIC_DIR", str(BACKEND_DIR.parent / "frontend" / "dist")))

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.data_dir / 'orbitdesk.db'}"


settings = Settings()
