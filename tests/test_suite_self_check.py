"""Negative tests for the test tooling itself.

A security check is only useful if it actually fails when something is wrong.
These tests start a deliberately misconfigured device and confirm the checks catch it.
"""
import socket

import pytest

from ndts.network import check_baseline, is_port_open, scan_ports, version_tuple
from simulator.device_sim import SimulatedDevice

HOST = "127.0.0.1"


def _free_port():
    with socket.socket() as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


@pytest.fixture
def insecure_device():
    """A second device with an open 'telnet' port and a stray debug port."""
    http, rtsp, telnet, stray = (_free_port() for _ in range(4))
    with SimulatedDevice(HOST, http, rtsp, open_extra_ports=[telnet, stray]) as dev:
        yield dev, {"http": http, "rtsp": rtsp, "telnet": telnet, "stray": stray}


@pytest.mark.selfcheck
def test_scanner_finds_exactly_the_open_ports(insecure_device):
    """SC-001: The scanner reports all open ports and no closed ones."""
    _, ports = insecure_device
    closed = _free_port()
    found = scan_ports(HOST, list(ports.values()) + [closed])
    assert found == set(ports.values())
    assert not is_port_open(HOST, closed)


@pytest.mark.selfcheck
def test_baseline_flags_forbidden_and_unexpected_ports(insecure_device):
    """SC-002: A forgotten telnet port is flagged as forbidden, a stray port as unexpected."""
    _, ports = insecure_device
    found = scan_ports(HOST, ports.values())
    result = check_baseline(found, expected={ports["http"], ports["rtsp"]}, forbidden={ports["telnet"]})
    assert not result.passed
    assert result.forbidden == {ports["telnet"]}
    assert result.unexpected == {ports["stray"]}
    assert result.missing == set()


@pytest.mark.selfcheck
def test_baseline_flags_missing_service():
    """SC-003: A service that should be up but isn't is reported as missing."""
    result = check_baseline(open_ports={80}, expected={80, 554}, forbidden={23})
    assert result.missing == {554}
    assert not result.passed


@pytest.mark.selfcheck
@pytest.mark.parametrize(
    "reported, minimum, ok",
    [("4.2.1", "4.2.0", True), ("4.2.0", "4.2.0", True), ("4.1.9", "4.2.0", False), ("4.10.0", "4.9.9", True)],
)
def test_firmware_version_comparison(reported, minimum, ok):
    """SC-004: Versions compare numerically (4.10 is newer than 4.9), not as text."""
    assert (version_tuple(reported) >= version_tuple(minimum)) is ok
