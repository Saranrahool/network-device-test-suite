"""Security baseline: only the expected services may be reachable."""
import pytest

from ndts.network import check_baseline


@pytest.mark.security
def test_expected_services_are_reachable(profile, open_ports):
    """NDT-001: Every service the device is supposed to offer is listening."""
    missing = {s.name: s.port for s in profile.expected_services if s.port not in open_ports}
    assert not missing, f"Expected services not reachable on {profile.host}: {missing}"


@pytest.mark.security
def test_forbidden_ports_are_closed(profile, open_ports):
    """NDT-002: Insecure services (telnet, FTP, TFTP, debug) are not exposed."""
    exposed = {port: profile.forbidden_ports[port] for port in open_ports & set(profile.forbidden_ports)}
    assert not exposed, f"Forbidden ports open on {profile.host}: {exposed}"


@pytest.mark.security
def test_no_unexpected_open_ports(profile, open_ports):
    """NDT-003: Nothing else in the scan range is open (attack surface check)."""
    result = check_baseline(open_ports, profile.expected_ports, set(profile.forbidden_ports))
    assert not result.unexpected, f"Unexpected open ports on {profile.host}: {sorted(result.unexpected)}"
