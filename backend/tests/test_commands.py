"""Tests für die Befehlsliste: Rechte, Vier-Augen-Prinzip, Senden nur im Überflug."""

from fastapi.testclient import TestClient

from app.clock import parse_iso
from app.main import app
from app.mission import mission

ANNA = {"X-OrbitDesk-User": "anna"}  # Operator
BEN = {"X-OrbitDesk-User": "ben"}  # Flight Director
CLARA = {"X-OrbitDesk-User": "clara"}  # Engineer (nur lesen)


def test_command_workflow():
    with TestClient(app) as client:
        # Vor einen Überflug springen und Befehl für genau diesen Überflug anlegen
        nxt = client.post("/api/sim/jump-to-next-pass").json()
        body = {"code": "HEATER_MODE", "args": {"mode": "ON"}, "pass_id": nxt["id"],
                "comment": "Heater thermostat failed"}
        assert client.post("/api/commands", json=body, headers=CLARA).status_code == 403
        r = client.post("/api/commands", json=body, headers=ANNA)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c["status"] == "awaiting_approval" and c["pass_id"] == nxt["id"]

        # Operator darf nicht freigeben; Flight Director schon
        assert client.post(f"/api/commands/{c['id']}/approve", headers=ANNA).status_code == 403
        assert client.post(f"/api/commands/{c['id']}/send", headers=ANNA).status_code == 409  # nicht freigegeben
        r = client.post(f"/api/commands/{c['id']}/approve", headers=BEN)
        assert r.json()["status"] == "approved" and r.json()["decided_by"] == "Ben"

        # Noch kein Kontakt (1 min vor AOS) → Senden abgelehnt
        r = client.post(f"/api/commands/{c['id']}/send", headers=ANNA)
        assert r.status_code == 409 and "contact" in r.json()["detail"].lower()

        # Mitten in den Überflug springen → Senden klappt, Satellit reagiert
        tca = parse_iso(nxt["tca"])
        mission.clock.jump_to(tca)
        mission.simulator.step_to(tca, random_faults=False)
        r = client.post(f"/api/commands/{c['id']}/send", headers=ANNA)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "sent" and r.json()["result"].startswith("ACK")
        assert mission.simulator.state.heater_mode == "ON"
        # Zweites Senden nicht möglich
        assert client.post(f"/api/commands/{c['id']}/send", headers=ANNA).status_code == 409

        # Alles steht im Protokoll
        actions = [e["action"] for e in client.get("/api/audit").json()]
        assert {"command.create", "command.approve", "command.send"} <= set(actions)


def test_four_eyes_principle():
    with TestClient(app) as client:
        r = client.post("/api/commands", json={"code": "PING"}, headers=BEN)
        assert r.status_code == 200
        r = client.post(f"/api/commands/{r.json()['id']}/approve", headers=BEN)
        assert r.status_code == 409 and "Four-eyes" in r.json()["detail"]


def test_reject_and_cancel():
    with TestClient(app) as client:
        c1 = client.post("/api/commands", json={"code": "RESET_ADCS"}, headers=ANNA).json()
        assert client.post(f"/api/commands/{c1['id']}/reject", json={"reason": " "},
                           headers=BEN).status_code == 409
        r = client.post(f"/api/commands/{c1['id']}/reject", json={"reason": "Not needed"}, headers=BEN)
        assert r.json()["status"] == "rejected"
        c2 = client.post("/api/commands", json={"code": "PING"}, headers=ANNA).json()
        assert client.post(f"/api/commands/{c2['id']}/cancel", headers=ANNA).json()["status"] == "cancelled"


def test_invalid_commands():
    with TestClient(app) as client:
        bad = [{"code": "SELF_DESTRUCT"},
               {"code": "SET_MODE", "args": {"mode": "TURBO"}},
               {"code": "PING", "args": {"x": "1"}},
               {"code": "PING", "pass_id": "P-19990101-0000"}]
        for body in bad:
            assert client.post("/api/commands", json=body, headers=ANNA).status_code == 409, body
