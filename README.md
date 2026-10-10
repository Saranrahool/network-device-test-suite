# Network Device Test Suite

[![Device tests](https://github.com/Saranrahool/network-device-test-suite/actions/workflows/tests.yml/badge.svg)](https://github.com/Saranrahool/network-device-test-suite/actions/workflows/tests.yml)

Automated **network, security and performance checks for networked field devices**, such as onboard cameras, mobile video recorders and data collectors, written in **Python and pytest**.

Each device has a YAML **profile** describing its expected network baseline. The suite scans the device and fails if anything doesn't match: a service is down, an insecure port like telnet is exposed, an unknown port is open, firmware is out of date, or response times drift past their thresholds.

A **simulated camera** is included, so the whole suite runs in CI without hardware.

## What it checks

| ID | Check | Category |
|----|-------|----------|
| NDT-001 | Every expected service is listening | Security baseline |
| NDT-002 | Insecure ports (telnet, FTP, TFTP, debug) are closed | Security baseline |
| NDT-003 | No unexpected open ports in the scan range (attack surface) | Security baseline |
| NDT-004 | Management API health endpoint returns 200 / `status: ok` | Functional |
| NDT-005 | Firmware is at or above the approved minimum version | Functional |
| NDT-006 | RTSP video port answers an `OPTIONS` request correctly | Functional |
| NDT-007 | TCP connect latency (p95) is under the threshold for every service | Performance |
| NDT-008 | Health endpoint response time is under the threshold | Performance |
| SC-001 to SC-004 | **Self-checks:** a deliberately misconfigured device is started and the suite must catch it | Negative testing |

The self-checks matter: a security test is only useful if it actually fails when something is wrong.

## Example: catching an insecure device
Start the simulator with a forgotten telnet port, then run the security checks against it:
```bash
python -m simulator.device_sim --insecure      # terminal 1
pytest --no-sim -m security                    # terminal 2
```
```
FAILED test_forbidden_ports_are_closed[simulated-camera]
  AssertionError: Forbidden ports open on 127.0.0.1: {18023: 'Telnet (unencrypted remote shell)'}
```

## Device profiles
```yaml
name: simulated-camera
host: 127.0.0.1
expected_services:
  - {name: http-management, port: 18080}
  - {name: rtsp-video, port: 18554}
forbidden_ports:
  18023: Telnet (unencrypted remote shell)
scan_ports: [18000-18100, 18443, 18554, 18888]
health_url: http://127.0.0.1:18080/api/health
min_firmware: "4.2.0"
performance: {max_connect_ms: 50, max_http_ms: 300, samples: 20}
```
See [`devices/`](devices). The simulator uses real port numbers offset by 18000 (80 → 18080, 554 → 18554) so it runs without admin rights. [`example-onboard-recorder.yaml`](devices/example-onboard-recorder.yaml) shows a profile for real hardware.

## Running
```bash
pip install -r requirements.txt

pytest                                   # all checks against the simulated camera
pytest -m security                       # security baseline only
pytest --junitxml=reports/junit.xml      # JUnit report for CI dashboards
pytest --no-sim --profiles devices/example-onboard-recorder.yaml   # a real device
```
> Only scan devices you own or are authorized to test.

## Project structure
```
ndts/network.py        Port scanner, baseline comparison, latency, HTTP and RTSP probes (standard library only)
ndts/profile.py        YAML profile loader
simulator/             Simulated camera: HTTP API, RTSP port, optional insecure ports
devices/               Device profiles (one per device or model)
tests/                 Security, functional, performance and self-check tests
```

## Defect found while building this
Under rapid repeated connections, the latency check intermittently timed out (~1 s stalls). The cause was the simulator's server using Python's default listen backlog of 5, so bursts of connections overflowed the accept queue and the kernel dropped connection attempts until it retried. Raising the backlog to 128 fixed it, and 3 consecutive full runs passed. Real devices with small connection queues can show the same symptom, which is why the latency test reports p95, median and max instead of a single sample.

## Author
Rahool Saran · [rahoolsaran.com](https://rahoolsaran.com) · [LinkedIn](https://linkedin.com/in/rahool-saran)
