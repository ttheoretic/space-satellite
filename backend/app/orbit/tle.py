"""
TLE-Bahndaten laden.

Eine TLE ("Two-Line Element Set") beschreibt die Umlaufbahn eines Satelliten
in zwei Textzeilen. Sie gilt für einen bestimmten Zeitpunkt, die "Epoche".
Je weiter man sich zeitlich von der Epoche entfernt, desto ungenauer wird die
Vorhersage: Bei niedrigen Bahnen bremst die Restatmosphäre den Satelliten, das
Modell kann das nur näherungsweise. Daher zeigt die Oberfläche das Alter an.

Reihenfolge der Quellen:
  1. LIVE      – frisch von CelesTrak geladen (alle paar Stunden neu)
  2. CACHE     – die zuletzt erfolgreich geladene TLE (Datei im data-Ordner)
  3. FALLBACK  – die mitgelieferte Ersatz-TLE (fallback_tle.txt, nur angenähert)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from skyfield.api import EarthSatellite, load

from ..clock import iso
from ..config import settings

log = logging.getLogger(__name__)

# Skyfield-Zeitskala (rechnet z. B. zwischen UTC und Terrestrischer Zeit um).
# builtin=True: nutzt eingebaute Tabellen, kein Download nötig.
ts = load.timescale(builtin=True)

FALLBACK_FILE = Path(__file__).with_name("fallback_tle.txt")


def _cache_file() -> Path:
    return settings.data_dir / f"tle_{settings.norad_id}.json"


def tle_checksum_ok(line: str) -> bool:
    """Prüft die Prüfziffer am Zeilenende (Ziffern zählen, '-' zählt als 1)."""
    if len(line) < 69:
        return False
    total = sum(int(c) if c.isdigit() else (1 if c == "-" else 0) for c in line[:68])
    return str(total % 10) == line[68]


def parse_tle(text: str, norad_id: int) -> tuple[str, str, str]:
    """Holt Name, Zeile 1 und Zeile 2 aus einem Text. Wirft ValueError bei Fehlern."""
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    for i, ln in enumerate(lines):
        if ln.startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
            l1, l2 = ln, lines[i + 1]
            name = lines[i - 1].strip() if i > 0 else f"NORAD {norad_id}"
            if int(l1[2:7]) != norad_id:
                raise ValueError(f"TLE gehört zu NORAD {l1[2:7]}, erwartet {norad_id}")
            if not (tle_checksum_ok(l1) and tle_checksum_ok(l2)):
                raise ValueError("TLE-Prüfsumme falsch")
            return name, l1, l2
    raise ValueError("Keine TLE im Text gefunden")


@dataclass
class TleInfo:
    name: str
    line1: str
    line2: str
    source: str  # "live" | "cache" | "fallback"
    fetched_at: datetime | None

    def __post_init__(self) -> None:
        self.satellite = EarthSatellite(self.line1, self.line2, self.name, ts)

    @property
    def epoch(self) -> datetime:
        return self.satellite.epoch.utc_datetime()

    def status(self, now: datetime) -> dict:
        """Zusammenfassung für die Oberfläche. Alter bezogen auf die Missionszeit."""
        age_days = (now - self.epoch).total_seconds() / 86400
        return {
            "name": self.name,
            "norad_id": settings.norad_id,
            "source": self.source,
            "epoch": iso(self.epoch),
            "fetched_at": iso(self.fetched_at) if self.fetched_at else None,
            "age_days": round(age_days, 2),
            "warn": age_days >= settings.tle_warn_age_days or self.source == "fallback",
            "warn_age_days": settings.tle_warn_age_days,
            "line1": self.line1,
            "line2": self.line2,
        }


class TleManager:
    """Hält die aktuell verwendete TLE und lädt bei Bedarf neu."""

    def __init__(self) -> None:
        self.current: TleInfo = self._load_cache() or self._load_fallback()
        self.last_error: str | None = None

    # -- Quellen ------------------------------------------------------------
    def _load_cache(self) -> TleInfo | None:
        try:
            raw = json.loads(_cache_file().read_text())
            name, l1, l2 = parse_tle("\n".join([raw["name"], raw["line1"], raw["line2"]]),
                                     settings.norad_id)
            return TleInfo(name, l1, l2, "cache", datetime.fromisoformat(raw["fetched_at"]))
        except FileNotFoundError:
            return None
        except Exception as exc:  # beschädigte Datei → ignorieren
            log.warning("TLE-Cache unbrauchbar: %s", exc)
            return None

    def _load_fallback(self) -> TleInfo:
        name, l1, l2 = parse_tle(FALLBACK_FILE.read_text(encoding="utf-8"), settings.norad_id)
        return TleInfo(name, l1, l2, "fallback", None)

    async def refresh_online(self) -> bool:
        """Versucht, eine aktuelle TLE von CelesTrak zu laden. True bei Erfolg."""
        if not settings.tle_online:
            return False
        url = settings.tle_url.format(norad=settings.norad_id)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            name, l1, l2 = parse_tle(resp.text, settings.norad_id)
        except Exception as exc:
            self.last_error = str(exc) or exc.__class__.__name__
            log.warning("TLE-Abruf fehlgeschlagen (%s), nutze %s", self.last_error,
                        self.current.source)
            return False

        now = datetime.now(timezone.utc)
        self.current = TleInfo(name, l1, l2, "live", now)
        self.last_error = None
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _cache_file().write_text(json.dumps(
            {"name": name, "line1": l1, "line2": l2, "fetched_at": now.isoformat()}))
        log.info("TLE geladen: Epoche %s", self.current.epoch.isoformat())
        return True
