"""Endpunkte der Befehlsliste. Die Regeln stehen in mission.py / commands.py."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import commands as cmd
from ..mission import mission
from ..schemas import CommandCreate, CommandReject, CommandSchedule
from ..users import User, require

router = APIRouter(prefix="/api/commands", tags=["commands"])


async def _run(coro) -> dict:
    """Übersetzt Regelverstöße in verständliche HTTP-Fehler."""
    try:
        return await coro
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Command {exc} not found") from exc
    except cmd.CommandError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/catalog")
def get_catalog() -> list[dict]:
    """Welche Befehle der Satellit versteht."""
    return cmd.catalog()


@router.get("")
def list_commands() -> list[dict]:
    """Alle Befehle, neueste zuerst."""
    return mission.list_commands()


@router.post("")
async def create(req: CommandCreate, user: User = Depends(require("command.create"))) -> dict:
    return await _run(mission.create_command(req.code, req.args, req.pass_id, req.comment, user.name))


@router.post("/{command_id}/schedule")
async def schedule(command_id: int, req: CommandSchedule,
                   user: User = Depends(require("command.schedule"))) -> dict:
    return await _run(mission.schedule_command(command_id, req.pass_id, user.name))


@router.post("/{command_id}/approve")
async def approve(command_id: int, user: User = Depends(require("command.approve"))) -> dict:
    return await _run(mission.approve_command(command_id, user.name))


@router.post("/{command_id}/reject")
async def reject(command_id: int, req: CommandReject,
                 user: User = Depends(require("command.approve"))) -> dict:
    return await _run(mission.reject_command(command_id, req.reason, user.name))


@router.post("/{command_id}/send")
async def send(command_id: int, user: User = Depends(require("command.send"))) -> dict:
    return await _run(mission.send_command(command_id, user.name))


@router.post("/{command_id}/cancel")
async def cancel(command_id: int, user: User = Depends(require("command.create"))) -> dict:
    return await _run(mission.cancel_command(command_id, user.name))
