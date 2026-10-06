import sys
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


print("==== served WSS snippets ====")
print(run(r"""docker exec skykin-web sh -c "grep -n 'agent_wss\|buildSipWsUrl\|wss://\|:5060\|/wss/' /var/www/fusionpbx/app/agent_dashboard/index.php | head -20" """))

print("==== live page WSS const ====")
print(run(r"""curl -sk 'https://127.0.0.1:8088/app/agent_dashboard/index.php' -o /tmp/dash.html -w '%{http_code}\n'; grep -n "serverWss\|wss://" /tmp/dash.html | head -15"""))

print("==== nginx wss + errors ====")
print(run("docker exec skykin-web sh -c 'grep -n proxy_pass /etc/nginx/sites-enabled/skykin.conf; tail -20 /var/log/nginx/error.log'"))

print("==== regs / channels ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | grep -E 'WSS-BIND|REGISTRATIONS|failed'"))

print("==== recent register / wss ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE '102@|REGISTER|websocket|WSS|7443' /var/log/freeswitch/freeswitch.log | tail -25\""))

print("==== local nginx /wss/ upgrade ====")
print(run(r"""python3 - <<'PY'
import ssl, socket
req = (
    "GET /wss/ HTTP/1.1\r\n"
    "Host: 196.189.236.140:8088\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
    "Sec-WebSocket-Version: 13\r\n"
    "Sec-WebSocket-Protocol: sip\r\n"
    "\r\n"
).encode()
ctx = ssl._create_unverified_context()
s = socket.create_connection(("127.0.0.1", 8088), 5)
ss = ctx.wrap_socket(s, server_hostname="196.189.236.140")
ss.sendall(req)
ss.settimeout(6)
print(ss.recv(500).decode("latin1", "replace"))
ss.close()
PY"""))

print("==== docker->7443 ====")
print(run("docker exec skykin-web sh -c 'command -v curl; curl -skI --max-time 5 https://172.22.0.1:7443/ | head -8'"))
print(run("iptables -L INPUT -n | grep -E '7443|5066' | head"))
c.close()

print("==== remote /wss/ from this PC ====")
try:
    req = (
        "GET /wss/ HTTP/1.1\r\n"
        "Host: 196.189.236.140:8088\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "Sec-WebSocket-Protocol: sip\r\n"
        "\r\n"
    ).encode()
    ctx = ssl._create_unverified_context()
    s = socket.create_connection((HOST, 8088), 8)
    ss = ctx.wrap_socket(s, server_hostname=HOST)
    ss.sendall(req)
    ss.settimeout(8)
    print(ss.recv(500).decode("latin1", "replace"))
    ss.close()
except Exception as e:
    print("remote fail", type(e).__name__, e)
