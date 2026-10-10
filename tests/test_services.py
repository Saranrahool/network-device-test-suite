"""Service checks: the device's services respond correctly, not just that ports are open."""
import pytest

from ndts.network import http_get_json, rtsp_options, version_tuple


@pytest.mark.functional
def test_health_endpoint_reports_ok(profile):
    """NDT-004: The management API health endpoint returns 200 and status 'ok'."""
    if not profile.health_url:
        pytest.skip("profile has no health_url")
    result = http_get_json(profile.health_url)
    assert result.status == 200
    assert result.body.get("status") == "ok", f"Health body: {result.body}"


@pytest.mark.functional
def test_firmware_meets_minimum_version(profile):
    """NDT-005: Reported firmware is at or above the minimum approved version."""
    if not (profile.health_url and profile.min_firmware):
        pytest.skip("profile has no firmware requirement")
    firmware = http_get_json(profile.health_url).body.get("firmware")
    assert firmware, "Device did not report a firmware version"
    assert version_tuple(firmware) >= version_tuple(profile.min_firmware), (
        f"Firmware {firmware} is below minimum {profile.min_firmware}"
    )


@pytest.mark.functional
def test_rtsp_video_service_answers(profile):
    """NDT-006: The RTSP video port speaks RTSP and accepts an OPTIONS request."""
    if not profile.rtsp_port:
        pytest.skip("profile has no rtsp_port")
    status_line = rtsp_options(profile.host, profile.rtsp_port)
    assert status_line.startswith("RTSP/1.0 200"), f"Unexpected RTSP reply: {status_line!r}"
