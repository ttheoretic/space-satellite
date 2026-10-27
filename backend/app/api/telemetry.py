"""Endpunkte für Telemetrie: aktueller Wert und Verlauf."""

from __future__ import annotations

import math
from datetime import timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from ..db import session_scope
from ..mission import mission
from ..models import TelemetryFrame

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("/latest")
def latest() -> dict | None:
    return mission.latest_frame


@router.get("/history")
def history(
    minutes: float = Query(180, gt=0, le=24 * 60, description="Zeitfenster in Minuten Missionszeit"),
    max_points: int = Query(600, ge=10, le=5000, description="Höchstzahl der Datenpunkte"),
) -> list[dict]:
    """
    Verlauf der letzten `minutes` Minuten. Sind es mehr Pakete als `max_points`,
    wird gleichmäßig ausgedünnt (jedes n-te Paket), damit der Browser flüssig bleibt.
    """
    since = mission.clock.now() - timedelta(minutes=minutes)
    with session_scope() as s:
        cond = TelemetryFrame.timestamp >= since
        count = s.scalar(select(func.count()).select_from(TelemetryFrame).where(cond)) or 0
        stride = max(1, math.ceil(count / max_points))
        query = select(TelemetryFrame.data).where(cond)
        if stride > 1:
            query = query.where(TelemetryFrame.id % stride == 0)
        return list(s.scalars(query.order_by(TelemetryFrame.timestamp)))
