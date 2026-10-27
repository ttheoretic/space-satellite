"""Tests für Überflugberechnung, Bodenstation und Vorspulen."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.orbit.passes import GroundStation, PassPredictor, look_angles
from app.orbit.tle import TleManager

BERLIN = GroundStation("TU Berlin", 52.51, 13.33, 60, 5)
T0 = datetime(2026, 10, 27, 15, tzinfo=timezone.utc)


def test_passes_are_plausible_for_leo():
    sat = TleManager().current.satellite
    passes = PassPredictor().get(sat, BERLIN, T0, hours=48)
    # Sonnensynchrone LEO-Bahn über Berlin: einige Überflüge pro Tag, je max. ~12 min
    assert 4 <= len(passes) <= 16
    for p in passes:
        assert p["aos"] < p["tca"] < p["los"]
        assert 60 <= p["duration_s"] <= 13 * 60
        assert 5 <= p["max_elevation"] <= 90
    # Elevation am höchsten Punkt stimmt mit direkter Rechnung überein
    tca = datetime.fromisoformat(passes[0]["tca"].replace("Z", "+00:00"))
    assert abs(look_angles(sat, BERLIN, tca)["elevation"] - passes[0]["max_elevation"]) < 0.2


def test_higher_mask_gives_fewer_passes():
    sat = TleManager().current.satellite
    low = PassPredictor().get(sat, BERLIN, T0)
    high = PassPredictor().get(sat, GroundStation("x", 52.51, 13.33, 60, 30), T0)
    assert len(high) < len(low)


def test_station_api_and_jump():
    with TestClient(app) as client:
        body = {"name": "Bad", "lat": 95, "lon": 0, "alt_m": 0, "min_elevation": 5}
        assert client.put("/api/station", json=body, headers={"X-OrbitDesk-User": "anna"}).status_code == 400
        body = {"name": "Munich", "lat": 48.15, "lon": 11.57, "alt_m": 520, "min_elevation": 5}
        assert client.put("/api/station", json=body, headers={"X-OrbitDesk-User": "clara"}).status_code == 403
        assert client.put("/api/station", json=body, headers={"X-OrbitDesk-User": "ben"}).status_code == 200
        data = client.get("/api/passes").json()
        assert data["station"]["name"] == "Munich" and data["passes"]
        first = data["passes"][0]
        assert client.get(f"/api/passes/{first['id']}").json()["track"]

        before = client.get("/api/status").json()["clock"]["mission_time"]
        r = client.post("/api/sim/jump-to-next-pass")
        assert r.status_code == 200
        after = client.get("/api/status").json()["clock"]["mission_time"]
        assert after > before
