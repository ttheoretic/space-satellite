"""Endpunkte für Alarme und Grenzwerte."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException

from ..limits import LimitSet, default_limits
from ..mission import mission
from ..parameters import PARAMETERS_BY_KEY
from ..schemas import AckRequest, LimitUpdate
from ..users import User, require

router = APIRouter(prefix="/api", tags=["alarms"])


@router.get("/alarms")
def open_alarms() -> list[dict]:
    """Alarme, die Aufmerksamkeit brauchen: aktiv und/oder unbestätigt."""
    return mission.alarms.list_open()


@router.get("/alarms/history")
def alarm_history(limit: int = 100) -> list[dict]:
    """Erledigte Alarme (abgeklungen und bestätigt)."""
    return mission.alarms.list_history(limit)


@router.post("/alarms/ack")
async def acknowledge(req: AckRequest, user: User = Depends(require("alarm.ack"))) -> list[dict]:
    """Alarme bestätigen (nur Operator und Flight Director)."""
    return await mission.acknowledge(req.ids, user.name)


@router.get("/limits")
def get_limits() -> list[dict]:
    return mission.alarms.limits_catalog()


@router.put("/limits/{key}")
async def put_limits(key: str, req: LimitUpdate,
                     user: User = Depends(require("limits.edit"))) -> list[dict]:
    """Grenzwerte eines Messwerts ändern (nur Operator und Flight Director)."""
    if key not in PARAMETERS_BY_KEY:
        raise HTTPException(status_code=404, detail=f"Unknown parameter {key}")
    try:
        await mission.update_limits(key, LimitSet(**req.model_dump()), user.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return mission.alarms.limits_catalog()


@router.post("/limits/{key}/reset")
async def reset_limits(key: str, user: User = Depends(require("limits.edit"))) -> list[dict]:
    """Grenzwerte auf die Standardwerte aus parameters.py zurücksetzen."""
    if key not in PARAMETERS_BY_KEY:
        raise HTTPException(status_code=404, detail=f"Unknown parameter {key}")
    await mission.update_limits(key, LimitSet(**asdict(default_limits(key))), user.name)
    return mission.alarms.limits_catalog()
