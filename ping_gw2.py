import socket
import ssl
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=20, allow_agent=False, look_for_keys=False)
_, o, e = c.exec_command("ss -lnt | grep 18081; journalctl -u skykin-ws-sip -n 5 --no-pager")
print(o.read().decode() + e.read().decode())
c.close()

req = (
    "GET /wss/ HTTP/1.1\r\nHost: 196.189.236.140:8088\r\nUpgrade: websocket\r\n"
    "Connection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
    "Sec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: sip\r\n\r\n"
).encode()
ctx = ssl._create_unverified_context()
s = socket.create_connection(("196.189.236.140", 8088), 8)
ss = ctx.wrap_socket(s, server_hostname="196.189.236.140")
ss.sendall(req)
ss.settimeout(6)
print(ss.recv(250).decode("latin1", "replace"))
ss.close()
