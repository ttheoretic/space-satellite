"""Tests für Grenzwerte, Hysterese, Alarm-Lebenslauf und Rollenrechte."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.limits import AlarmEngine, LimitSet
from app.main import app

T0 = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)


def frame(temp: float) -> dict:
    return {"values": {"battery_temp": temp}}


@pytest.fixture()
def engine():
    init_db()
    eng = AlarmEngine()
    eng.load()
    eng.reset()
    # Batterietemperatur: kritisch < -5, Warnung < 0 (Spanne 50 °C → Totband 1 °C)
    eng.limits = {"battery_temp": LimitSet(-5, 0, 40, 45)}
    return eng


def test_classify():
    ls = LimitSet(-5, 0, 40, 45)
    assert ls.classify(20)[0] == "ok"
    assert ls.classify(-1)[0] == "warning"
    assert ls.classify(-6) == ("critical", "< -5")
    assert ls.classify(46)[0] == "critical"


def test_limits_must_increase():
    with pytest.raises(ValueError):
        LimitSet(0, -5, 40, 45).validate()
    LimitSet(None, 0, None, 45).validate()  # einzelne Grenzen dürfen fehlen


def test_hysteresis_prevents_flapping(engine):
    [alarm] = engine.process(frame(-0.1), T0)
    assert alarm["severity"] == "warning" and alarm["active"]
    # knapp über der Grenze (innerhalb des Totbands von 1 °C): Alarm bleibt
    assert engine.process(frame(0.3), T0 + timedelta(seconds=1)) == []
    assert engine.process(frame(-0.2), T0 + timedelta(seconds=2)) == []
    # deutlich zurück im guten Bereich: Alarm klingt ab
    [cleared] = engine.process(frame(2.0), T0 + timedelta(seconds=3))
    assert cleared["id"] == alarm["id"] and not cleared["active"]


def test_escalation_requires_new_ack(engine):
    [a] = engine.process(frame(-1), T0)
    engine.acknowledge([a["id"]], "Anna", T0)
    [esc] = engine.process(frame(-6), T0 + timedelta(seconds=1))
    assert esc["severity"] == "critical" and not esc["acknowledged"]


def test_cleared_and_acked_alarm_moves_to_history(engine):
    [a] = engine.process(frame(-1), T0)
    engine.process(frame(5), T0 + timedelta(seconds=1))
    assert any(x["id"] == a["id"] for x in engine.list_open())  # noch unbestätigt
    engine.acknowledge(None, "Ben", T0 + timedelta(seconds=2))
    assert all(x["id"] != a["id"] for x in engine.list_open())
    assert any(x["id"] == a["id"] for x in engine.list_history())


def test_frame_gets_limit_status(engine):
    f = frame(-6)
    engine.process(f, T0)
    assert f["limits"] == {"battery_temp": "critical"}


def test_roles():
    with TestClient(app) as client:
        body = {"crit_low": -5, "warn_low": 0, "warn_high": 40, "crit_high": 45}
        assert client.put("/api/limits/battery_temp", json=body).status_code == 401
        r = client.put("/api/limits/battery_temp", json=body, headers={"X-OrbitDesk-User": "clara"})
        assert r.status_code == 403  # Engineer: nur Lesezugriff
        r = client.put("/api/limits/battery_temp", json=body, headers={"X-OrbitDesk-User": "anna"})
        assert r.status_code == 200
        bad = {**body, "warn_low": -10}
        r = client.put("/api/limits/battery_temp", json=bad, headers={"X-OrbitDesk-User": "anna"})
        assert r.status_code == 400
        assert client.post("/api/alarms/ack", json={}, headers={"X-OrbitDesk-User": "clara"}).status_code == 403
        assert client.post("/api/alarms/ack", json={}, headers={"X-OrbitDesk-User": "ben"}).status_code == 200
        audit = client.get("/api/audit").json()
        assert audit[0]["user"] in ("Anna", "Ben")


def test_fault_trigger_endpoint():
    with TestClient(app) as client:
        assert client.post("/api/sim/faults/heater_failure").status_code == 200
        assert client.post("/api/sim/faults/does_not_exist").status_code == 404
        assert client.post("/api/sim/faults/clear").status_code == 200
