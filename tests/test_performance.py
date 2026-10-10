"""Responsiveness checks against the thresholds in each device profile."""
import pytest

from ndts.network import http_get_json, tcp_connect_latency


@pytest.mark.performance
def test_tcp_connect_latency(profile):
    """NDT-007: 95% of TCP connections to each service complete under the threshold."""
    for service in profile.expected_services:
        stats = tcp_connect_latency(profile.host, service.port, samples=profile.latency_samples)
        assert stats.p95 <= profile.max_connect_ms, (
            f"{service.name}: p95 {stats.p95:.1f} ms > {profile.max_connect_ms} ms "
            f"(median {stats.median:.1f} ms, max {stats.maximum:.1f} ms)"
        )


@pytest.mark.performance
def test_health_endpoint_response_time(profile):
    """NDT-008: The health endpoint responds within the threshold."""
    if not profile.health_url:
        pytest.skip("profile has no health_url")
    http_get_json(profile.health_url)  # warm-up request
    result = http_get_json(profile.health_url)
    assert result.elapsed_ms <= profile.max_http_ms, f"{result.elapsed_ms:.1f} ms > {profile.max_http_ms} ms"
