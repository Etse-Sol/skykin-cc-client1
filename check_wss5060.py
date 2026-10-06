import sys
import time
import ssl
import socket
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HOST = "196.189.236.140"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== regs ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))
print("==== bind ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | grep -E 'BIND|WSS|WS-|failed|REGISTRATIONS'"))
print("==== disable-tcp context ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -n -B2 -A2 disable-tcp /etc/freeswitch/sip_profiles/internal.xml\""))
print("==== recent wss/ws ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'WSS|websocket|5060|handshake|SSL|tport' /var/log/freeswitch/freeswitch.log | tail -30\""))

print("==== local WS upgrade on 5060 ====")
print(run(r"""python3 - <<'PY'
import ssl, socket
req = (
    "GET / HTTP/1.1\r\n"
    "Host: 196.189.236.140:5060\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
    "Sec-WebSocket-Version: 13\r\n"
    "Sec-WebSocket-Protocol: sip\r\n"
    "\r\n"
).encode()
ctx = ssl._create_unverified_context()
s = socket.create_connection(("127.0.0.1", 5060), 5)
ss = ctx.wrap_socket(s, server_hostname="196.189.236.140")
ss.sendall(req)
ss.settimeout(5)
print(ss.recv(800).decode("latin1", "replace"))
ss.close()
PY"""))
c.close()

print("==== remote WS upgrade on 5060 ====")
try:
    req = (
        "GET / HTTP/1.1\r\n"
        "Host: 196.189.236.140:5060\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "Sec-WebSocket-Protocol: sip\r\n"
        "\r\n"
    ).encode()
    ctx = ssl._create_unverified_context()
    s = socket.create_connection((HOST, 5060), 5)
    ss = ctx.wrap_socket(s, server_hostname=HOST)
    ss.sendall(req)
    ss.settimeout(5)
    print(ss.recv(800).decode("latin1", "replace"))
    ss.close()
except Exception as e:
    print("remote fail", type(e), e)
