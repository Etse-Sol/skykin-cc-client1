import socket
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HOST = "196.189.236.140"
# Chrome-safe ports we might already have open, plus a few extras
ports = [
    80, 443, 3000, 3443, 4443, 4444, 5000, 5001, 7880, 8000, 8080, 8081,
    8082, 8088, 8090, 8443, 8444, 8888, 9000, 9001, 9080, 9090, 9443,
    10443, 2083, 2087, 2096, 7443, 7444, 5066, 5060,
]


def probe(port, timeout=2.5):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((HOST, port))
        s.close()
        return "OPEN"
    except Exception as e:
        return type(e).__name__


for p in ports:
    print(f"{p}: {probe(p)}")
