"""
Einstiegspunkt des Backends.

Start (Entwicklung):  uvicorn app.main:app --reload --port 8000
API-Dokumentation:    http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from .api import system, telemetry
from .config import settings
from .db import init_db
from .mission import mission

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Läuft beim Start des Servers …
    init_db()
    await mission.start()
    yield
    # … und beim Beenden.
    await mission.stop()


app = FastAPI(title="OrbitDesk API", version="0.1.0", lifespan=lifespan)
app.include_router(system.router)
app.include_router(telemetry.router)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Live-Kanal: Der Browser verbindet sich einmal und bekommt dann laufend
    Telemetrie, Ereignisse und Statusänderungen geschickt."""
    await mission.broadcaster.connect(ws)
    try:
        await mission.broadcaster.send(ws, {"type": "status", "status": mission.status()})
        if mission.latest_frame:
            await mission.broadcaster.send(ws, {"type": "telemetry", "frame": mission.latest_frame})
        while True:
            await ws.receive_text()  # Wir erwarten nichts, halten nur die Verbindung offen
    except WebSocketDisconnect:
        pass
    finally:
        mission.broadcaster.disconnect(ws)


# Gebaute Oberfläche ausliefern (falls vorhanden). Muss nach den API-Routen
# stehen, damit "/" nicht die API verdeckt.
if settings.static_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="frontend")
