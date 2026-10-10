"""Network checks: TCP port scanning, latency sampling, HTTP and RTSP probes.

Uses only the Python standard library (no nmap needed), so the suite runs the
same on Windows, Linux and in CI. Only scan devices you own or are authorized to test.
"""
import json
import socket
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """TCP connect check: True if something is accepting connections on the port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def scan_ports(host: str, ports, timeout: float = 0.5, workers: int = 64) -> set[int]:
    """Return the set of open ports among `ports`, scanned concurrently."""
    ports = list(ports)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(lambda p: (p, is_port_open(host, p, timeout)), ports)
    return {port for port, is_open in results if is_open}


@dataclass
class BaselineResult:
    missing: set[int]       # expected but closed
    forbidden: set[int]     # must be closed but open
    unexpected: set[int]    # open but not in the expected list

    @property
    def passed(self) -> bool:
        return not (self.missing or self.forbidden or self.unexpected)


def check_baseline(open_ports: set[int], expected: set[int], forbidden: set[int]) -> BaselineResult:
    """Compare a scan against the device's expected security baseline."""
    return BaselineResult(
        missing=expected - open_ports,
        forbidden=open_ports & forbidden,
        unexpected=open_ports - expected - forbidden,
    )


@dataclass
class LatencyStats:
    samples_ms: list[float]

    @property
    def median(self) -> float:
        return statistics.median(self.samples_ms)

    @property
    def p95(self) -> float:
        ordered = sorted(self.samples_ms)
        return ordered[max(0, round(0.95 * len(ordered)) - 1)]

    @property
    def maximum(self) -> float:
        return max(self.samples_ms)


def tcp_connect_latency(host: str, port: int, samples: int = 20, timeout: float = 1.0) -> LatencyStats:
    """Time how long a TCP handshake takes, `samples` times."""
    results = []
    for _ in range(samples):
        start = time.perf_counter()
        with socket.create_connection((host, port), timeout=timeout):
            pass
        results.append((time.perf_counter() - start) * 1000)
    return LatencyStats(results)


@dataclass
class HttpResult:
    status: int
    elapsed_ms: float
    body: dict


def http_get_json(url: str, timeout: float = 2.0) -> HttpResult:
    start = time.perf_counter()
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        raw = resp.read()
        status = resp.status
    elapsed = (time.perf_counter() - start) * 1000
    return HttpResult(status=status, elapsed_ms=elapsed, body=json.loads(raw or b"{}"))


def rtsp_options(host: str, port: int, timeout: float = 2.0) -> str:
    """Send an RTSP OPTIONS request and return the status line, e.g. 'RTSP/1.0 200 OK'."""
    request = f"OPTIONS rtsp://{host}:{port}/ RTSP/1.0\r\nCSeq: 1\r\n\r\n".encode()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(request)
        reply = sock.recv(1024).decode(errors="replace")
    return reply.splitlines()[0] if reply else ""


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))
