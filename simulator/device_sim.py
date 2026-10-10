"""Simulated onboard camera, so the suite can run without real hardware.

It exposes the same kinds of services a networked camera/recorder would:
  - an HTTP management API with a JSON health endpoint
  - an RTSP video port that answers OPTIONS requests
  - optionally, "debug" ports left open by mistake (to prove the security checks catch them)

Real devices use ports like 80 and 554. Those need admin rights to open, so the
simulator uses the same numbers offset by 18000 (18080, 18554).

Run standalone:  python -m simulator.device_sim --insecure
"""
import argparse
import json
import socket
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _HealthHandler(BaseHTTPRequestHandler):
    firmware = "4.2.1"

    def do_GET(self):
        if self.path == "/api/health":
            body = json.dumps({"status": "ok", "device": "CAM-SIM-01", "firmware": self.firmware}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass


class _RtspHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(1024).decode(errors="replace")
        cseq = next((ln.split(":", 1)[1].strip() for ln in data.splitlines() if ln.lower().startswith("cseq")), "0")
        if data.startswith("OPTIONS"):
            reply = f"RTSP/1.0 200 OK\r\nCSeq: {cseq}\r\nPublic: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN\r\n\r\n"
        else:
            reply = f"RTSP/1.0 405 Method Not Allowed\r\nCSeq: {cseq}\r\n\r\n"
        self.request.sendall(reply.encode())


class _ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128


class _HttpServer(ThreadingHTTPServer):
    request_queue_size = 128  # default of 5 drops connections under rapid probing


class SimulatedDevice:
    def __init__(self, host="127.0.0.1", http_port=18080, rtsp_port=18554, open_extra_ports=(), firmware="4.2.1"):
        self.host = host
        self.http_port = http_port
        self.rtsp_port = rtsp_port
        self.open_extra_ports = list(open_extra_ports)
        self.firmware = firmware
        self._servers = []
        self._extra_sockets = []

    def start(self):
        handler = type("Handler", (_HealthHandler,), {"firmware": self.firmware})
        http_server = _HttpServer((self.host, self.http_port), handler)
        rtsp_server = _ReusableTCPServer((self.host, self.rtsp_port), _RtspHandler)
        for server in (http_server, rtsp_server):
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self._servers.append(server)
        for port in self.open_extra_ports:  # e.g. a forgotten telnet/debug listener
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, port))
            sock.listen()
            self._extra_sockets.append(sock)
        return self

    def stop(self):
        for server in self._servers:
            server.shutdown()
            server.server_close()
        for sock in self._extra_sockets:
            sock.close()
        self._servers.clear()
        self._extra_sockets.clear()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


def main():
    parser = argparse.ArgumentParser(description="Run a simulated network camera.")
    parser.add_argument("--insecure", action="store_true", help="also open a debug telnet port (18023)")
    args = parser.parse_args()
    extra = [18023] if args.insecure else []
    with SimulatedDevice(open_extra_ports=extra) as dev:
        print(f"Simulated device on {dev.host}: HTTP {dev.http_port}, RTSP {dev.rtsp_port}, extra {extra or 'none'}")
        print("Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
