"""Tests der REST-API und des WebSockets (ohne Netzwerk, mit Test-Datenbank)."""

from fastapi.testclient import TestClient

from app.main import app


def test_status_and_history():
    with TestClient(app) as client:
        status = client.get("/api/status").json()
        assert status["satellite"]["norad_id"] == 59112
        assert status["tle"]["source"] in ("cache", "fallback")
        assert status["clock"]["speed_options"] == [1, 10, 60]

        history = client.get("/api/telemetry/history?minutes=60").json()
        assert len(history) > 10  # Vorlauf wurde simuliert
        assert "battery_soc" in history[-1]["values"]


def test_speed_validation():
    with TestClient(app) as client:
        assert client.post("/api/sim/speed", json={"speed": 60}).status_code == 200
        assert client.post("/api/sim/speed", json={"speed": 7}).status_code == 400
        client.post("/api/sim/speed", json={"speed": 1})


def test_websocket_sends_status_first():
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "status"
