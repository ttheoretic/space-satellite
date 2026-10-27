"""
WebSocket-Verteiler.

Ein WebSocket ist eine dauerhaft offene Verbindung zwischen Browser und
Server. Anders als bei normalen HTTP-Anfragen kann der Server darüber jederzeit
von sich aus Daten schicken – ideal für Live-Telemetrie.
"""

from __future__ import annotations

import json
import logging

from fastapi import WebSocket

log = logging.getLogger(__name__)


class Broadcaster:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def send(self, ws: WebSocket, message: dict) -> None:
        await ws.send_text(json.dumps(message))

    async def broadcast(self, message: dict) -> None:
        """Schickt eine Nachricht an alle verbundenen Browser."""
        text = json.dumps(message)
        for ws in list(self._clients):
            try:
                await ws.send_text(text)
            except Exception:  # Browser-Tab geschlossen o. ä.
                self.disconnect(ws)

    @property
    def client_count(self) -> int:
        return len(self._clients)
