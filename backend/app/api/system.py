"""Endpunkte für Status, Missionsuhr, TLE und Simulator-Steuerung."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import audit
from ..mission import mission
from ..parameters import parameter_catalog
from ..schemas import SpeedRequest, ToggleRequest
from ..simulator.faults import FAULT_TYPES_BY_KEY, fault_catalog
from ..users import user_catalog

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/status")
def get_status() -> dict:
    """Satellit, Bodenstation, Missionsuhr und TLE-Zustand."""
    return mission.status()


@router.get("/parameters")
def get_parameters() -> list[dict]:
    """Katalog aller Telemetrie-Messwerte mit Einheit und Standard-Grenzwerten."""
    return parameter_catalog()


@router.get("/faults")
def get_faults() -> list[dict]:
    """Katalog der simulierbaren Fehlerbilder."""
    return fault_catalog()


@router.get("/users")
def get_users() -> list[dict]:
    """Die Demo-Personen mit Rolle und Rechten."""
    return user_catalog()


@router.get("/audit")
def get_audit(limit: int = 200) -> list[dict]:
    """Protokoll der Bedienaktionen, neueste zuerst."""
    return audit.recent(limit)


@router.get("/events")
def get_events() -> list[dict]:
    """Die letzten Bordereignisse (Eklipse, Moduswechsel, Fehler …), neueste zuerst."""
    return list(reversed(mission.simulator.events))


@router.post("/sim/speed")
async def set_speed(req: SpeedRequest) -> dict:
    """Zeitraffer einstellen (1×, 10× oder 60×)."""
    try:
        await mission.set_speed(req.speed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return mission.status()["clock"]


@router.post("/sim/reset")
async def reset_demo() -> dict:
    """Demo komplett zurücksetzen (Telemetrie, Uhr, Satellitenzustand)."""
    await mission.reset()
    return {"ok": True}


@router.post("/tle/refresh")
async def refresh_tle() -> dict:
    """TLE sofort neu von CelesTrak laden."""
    ok = await mission.refresh_tle()
    return {"ok": ok, "tle": mission.status()["tle"]}


# --- Demo-Steuerung ----------------------------------------------------------
# Diese Endpunkte gehören nicht zum späteren Betrieb, sondern steuern den
# Simulator während einer Vorführung. Deshalb gibt es hier keine Rollenprüfung.

@router.post("/sim/faults/clear")
async def clear_faults() -> dict:
    """Alle simulierten Fehler sofort beheben."""
    await mission.clear_faults()
    return {"ok": True}


@router.post("/sim/faults/{key}")
async def trigger_fault(key: str) -> dict:
    """Einen Fehler gezielt auslösen (z. B. heater_failure)."""
    if key not in FAULT_TYPES_BY_KEY:
        raise HTTPException(status_code=404, detail=f"Unknown fault {key}")
    await mission.trigger_fault(key)
    return {"ok": True}


@router.post("/sim/random-faults")
async def set_random_faults(req: ToggleRequest) -> dict:
    """Zufällige Fehler ein- oder ausschalten."""
    await mission.set_random_faults(req.enabled)
    return {"enabled": req.enabled}
