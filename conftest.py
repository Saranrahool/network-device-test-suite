"""Profile selection, simulator startup and shared scan results."""
from pathlib import Path

import pytest

from ndts.network import scan_ports
from ndts.profile import load_profile, load_profiles
from simulator.device_sim import SimulatedDevice

DEVICES_DIR = Path(__file__).parent / "devices"


def pytest_addoption(parser):
    parser.addoption("--profiles", nargs="+", help="device profile YAML files (default: every enabled profile in devices/)")
    parser.addoption("--no-sim", action="store_true", help="don't start the built-in simulated camera")


def _selected_profiles(config):
    paths = config.getoption("--profiles")
    profiles = [load_profile(p) for p in paths] if paths else load_profiles(DEVICES_DIR)
    return [p for p in profiles if p.enabled]


def pytest_generate_tests(metafunc):
    """Run every device test once per enabled profile, named after the device."""
    if "profile" in metafunc.fixturenames:
        profiles = _selected_profiles(metafunc.config)
        metafunc.parametrize("profile", profiles, ids=[p.name for p in profiles], scope="session")


@pytest.fixture(scope="session", autouse=True)
def simulator(request):
    """Start the simulated camera for the session, unless --no-sim is given."""
    if request.config.getoption("--no-sim"):
        yield None
        return
    with SimulatedDevice() as device:
        yield device


_scan_cache = {}


@pytest.fixture(scope="session")
def open_ports(profile):
    """Scan each device once per session and share the result across tests."""
    if profile.name not in _scan_cache:
        _scan_cache[profile.name] = scan_ports(profile.host, profile.scan_ports)
    return _scan_cache[profile.name]
