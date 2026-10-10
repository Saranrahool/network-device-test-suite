"""Device profiles: the expected network baseline for one device, loaded from YAML."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Service:
    name: str
    port: int


@dataclass
class DeviceProfile:
    name: str
    host: str
    expected_services: list[Service]
    forbidden_ports: dict[int, str]
    scan_ports: list[int]
    health_url: str | None = None
    rtsp_port: int | None = None
    min_firmware: str | None = None
    max_connect_ms: float = 50.0
    max_http_ms: float = 300.0
    latency_samples: int = 20
    enabled: bool = True
    source: Path | None = field(default=None, repr=False)

    @property
    def expected_ports(self) -> set[int]:
        return {s.port for s in self.expected_services}


def _expand_ports(spec) -> list[int]:
    """Accept a list of ints and 'start-end' ranges, e.g. [22, 80, '18000-18100']."""
    ports: set[int] = set()
    for item in spec or []:
        if isinstance(item, int):
            ports.add(item)
        else:
            start, end = (int(x) for x in str(item).split("-"))
            ports.update(range(start, end + 1))
    return sorted(ports)


def load_profile(path: str | Path) -> DeviceProfile:
    path = Path(path)
    data = yaml.safe_load(path.read_text())
    services = [Service(name=s["name"], port=int(s["port"])) for s in data.get("expected_services", [])]
    forbidden = {int(p): str(desc) for p, desc in (data.get("forbidden_ports") or {}).items()}
    scan = set(_expand_ports(data.get("scan_ports"))) | {s.port for s in services} | set(forbidden)
    perf = data.get("performance", {})
    return DeviceProfile(
        name=data["name"],
        host=data["host"],
        expected_services=services,
        forbidden_ports=forbidden,
        scan_ports=sorted(scan),
        health_url=data.get("health_url"),
        rtsp_port=data.get("rtsp_port"),
        min_firmware=data.get("min_firmware"),
        max_connect_ms=float(perf.get("max_connect_ms", 50)),
        max_http_ms=float(perf.get("max_http_ms", 300)),
        latency_samples=int(perf.get("samples", 20)),
        enabled=bool(data.get("enabled", True)),
        source=path,
    )


def load_profiles(directory: str | Path) -> list[DeviceProfile]:
    return [load_profile(p) for p in sorted(Path(directory).glob("*.yaml"))]
