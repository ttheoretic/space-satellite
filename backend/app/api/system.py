"""Endpunkte für Status, Missionsuhr, TLE und Simulator-Steuerung."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..mission import mission
from ..parameters import parameter_catalog
from ..schemas import SpeedRequest
from ..simulator.faults import fault_catalog

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
