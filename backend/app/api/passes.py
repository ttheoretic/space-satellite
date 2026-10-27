"""Endpunkte für Bodenstation und Überflüge."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..clock import iso
from ..mission import mission
from ..orbit.passes import GroundStation
from ..schemas import StationUpdate
from ..users import User, require

router = APIRouter(prefix="/api", tags=["passes"])


@router.get("/station")
def get_station() -> dict:
    return mission.station.to_dict()


@router.put("/station")
async def put_station(req: StationUpdate, user: User = Depends(require("station.edit"))) -> dict:
    """Bodenstation ändern (nur Operator und Flight Director)."""
    try:
        await mission.update_station(GroundStation(**req.model_dump()), user.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return mission.station.to_dict()


@router.get("/passes")
def get_passes(hours: float = Query(48, gt=0, le=168)) -> dict:
    """Überflüge über der Bodenstation in den nächsten `hours` Stunden (Missionszeit)."""
    return {
        "station": mission.station.to_dict(),
        "generated_at": iso(mission.clock.now()),
        "hours": hours,
        "tle_source": mission.tle.current.source,
        "passes": mission.get_passes(hours),
    }


@router.get("/passes/{pass_id}")
def get_pass(pass_id: str) -> dict:
    """Ein Überflug mit seiner Bahn am Himmel (für die Himmelskarte)."""
    p = mission.get_pass_track(pass_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Pass {pass_id} not found")
    return p


@router.post("/sim/jump-to-next-pass")
async def jump_to_next_pass() -> dict:
    """Demo: bis 1 Minute vor den nächsten Überflug vorspulen."""
    try:
        return await mission.jump_to_next_pass()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
