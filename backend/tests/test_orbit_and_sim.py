"""Tests für Bahndaten, Sonnenstand/Schatten und Simulator-Physik."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.clock import MissionClock
from app.orbit.tle import FALLBACK_FILE, TleManager, parse_tle, tle_checksum_ok
from app.simulator.cubesat import CubeSatSimulator
from app.simulator.sun import R_EARTH_KM, sun_position_km, sunlit_fraction


def test_fallback_tle_is_valid():
    name, l1, l2 = parse_tle(FALLBACK_FILE.read_text(), 59112)
    assert name == "SONATE-2"
    assert tle_checksum_ok(l1) and tle_checksum_ok(l2)


def test_parse_tle_rejects_wrong_object_and_garbage():
    with pytest.raises(ValueError):
        parse_tle(FALLBACK_FILE.read_text(), 12345)
    with pytest.raises(ValueError):
        parse_tle("<html>Service unavailable</html>", 59112)


def test_sun_distance_is_about_one_au():
    d = np.linalg.norm(sun_position_km(datetime(2026, 1, 3, tzinfo=timezone.utc)))
    assert 0.98 * 1.496e8 < d < 0.99 * 1.496e8  # Perihel Anfang Januar


def test_shadow_geometry():
    sun = sun_position_km(datetime(2026, 6, 1, tzinfo=timezone.utc))
    u = sun / np.linalg.norm(sun)
    r = R_EARTH_KM + 500
    assert sunlit_fraction(u * r, sun) == 1.0  # zwischen Erde und Sonne
    assert sunlit_fraction(-u * r, sun) == 0.0  # genau hinter der Erde


def test_orbit_has_realistic_eclipse_share():
    """Über einige Umläufe sollte der Satellit ~25–40 % der Zeit im Schatten sein."""
    tle = TleManager().current
    sim = CubeSatSimulator(lambda: tle.satellite, seed=1)
    t0 = datetime(2026, 10, 27, tzinfo=timezone.utc)
    frames = [sim.step_to(t0 + timedelta(seconds=s), random_faults=False)
              for s in range(0, 4 * 3600, 30)]
    share = sum(f["eclipse"] for f in frames) / len(frames)
    assert 0.25 < share < 0.40
    socs = [f["values"]["battery_soc"] for f in frames]
    assert max(socs) - min(socs) > 5  # Batterie lädt und entlädt sichtbar


def test_heater_failure_cools_battery_below_zero():
    tle = TleManager().current
    sim = CubeSatSimulator(lambda: tle.satellite, seed=2)
    t0 = datetime(2026, 10, 27, tzinfo=timezone.utc)
    sim.trigger_fault("heater_failure")
    temps = [sim.step_to(t0 + timedelta(seconds=s), random_faults=False)["values"]["battery_temp"]
             for s in range(0, 4 * 3600, 30)]
    assert min(temps) < 0


def test_safe_mode_clears_latchup():
    tle = TleManager().current
    sim = CubeSatSimulator(lambda: tle.satellite, seed=3)
    t0 = datetime(2026, 10, 27, tzinfo=timezone.utc)
    sim.trigger_fault("payload_latchup")
    assert sim.step_to(t0, random_faults=False)["values"]["power_consumption"] > 12
    sim.set_mode("SAFE")
    frame = sim.step_to(t0 + timedelta(seconds=60), random_faults=False)
    assert "payload_latchup" not in frame["faults"]


def test_clock_speed_change_does_not_jump():
    clock = MissionClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    before = clock.now()
    clock.set_speed(60)
    assert abs((clock.now() - before).total_seconds()) < 1
