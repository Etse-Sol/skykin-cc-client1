import sys
import time
import ssl
import socket
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HOST = "196.189.236.140"
LOCAL_PHP = r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=50):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


sftp = c.open_sftp()
with open(LOCAL_PHP, "rb") as f:
    data = f.read()
with sftp.file("/opt/call-center-deployement/call-center/app/agent_dashboard/index.php", "wb") as rf:
    rf.write(data)
sftp.close()
print("uploaded php", len(data))

print(run(r"""
docker exec skykin-freeswitch sh -c '
f=/etc/freeswitch/sip_profiles/internal.xml
sed -i "s#<param name=\"wss-binding\".*#<param name=\"wss-binding\" value=\"0.0.0.0:7443\"/>#" "$f"
grep -n "wss-binding\\|disable-tcp" "$f"
'
"""))

print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal restart'"))
time.sleep(3)
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | grep -E 'BIND-URL|WSS-BIND|WS-BIND'"))

print("==== iptables redirect 5060 -> 7443 ====")
print(run(r"""
# Remove any previous copies, then insert at top of PREROUTING
iptables -t nat -D PREROUTING -p tcp --dport 5060 -j REDIRECT --to-ports 7443 2>/dev/null || true
iptables -t nat -I PREROUTING 1 -p tcp --dport 5060 -j REDIRECT --to-ports 7443
# Persist
mkdir -p /etc/skykin
cat > /etc/skykin/wss-5060-redirect.sh <<'SH'
#!/bin/sh
iptables -t nat -C PREROUTING -p tcp --dport 5060 -j REDIRECT --to-ports 7443 2>/dev/null \
  || iptables -t nat -I PREROUTING 1 -p tcp --dport 5060 -j REDIRECT --to-ports 7443
SH
chmod +x /etc/skykin/wss-5060-redirect.sh
grep -q wss-5060-redirect /etc/rc.local 2>/dev/null || {
  if [ ! -f /etc/rc.local ]; then
    printf '#!/bin/sh\nexit 0\n' > /etc/rc.local
    chmod +x /etc/rc.local
  fi
  sed -i 's#^exit 0#/etc/skykin/wss-5060-redirect.sh\nexit 0#' /etc/rc.local
}
(crontab -l 2>/dev/null | grep -v wss-5060-redirect; echo '@reboot /etc/skykin/wss-5060-redirect.sh') | crontab -
iptables -t nat -L PREROUTING -n --line-numbers | head -15
"""))

print("==== local 7443 WS ====")
print(run(r"""python3 - <<'PY'
import ssl, socket
req = (
    "GET / HTTP/1.1\r\nHost: 127.0.0.1:7443\r\nUpgrade: websocket\r\n"
    "Connection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
    "Sec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: sip\r\n\r\n"
).encode()
ctx = ssl._create_unverified_context()
s = socket.create_connection(("127.0.0.1", 7443), 5)
ss = ctx.wrap_socket(s, server_hostname="196.189.236.140")
ss.sendall(req)
ss.settimeout(5)
print(ss.recv(200).decode("latin1", "replace").split("\r\n")[0])
ss.close()
PY"""))
c.close()

print("==== remote 5060 TLS+WS ====")
try:
    req = (
        "GET / HTTP/1.1\r\nHost: 196.189.236.140:5060\r\nUpgrade: websocket\r\n"
        "Connection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        "Sec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: sip\r\n\r\n"
    ).encode()
    ctx = ssl._create_unverified_context()
    s = socket.create_connection((HOST, 5060), 8)
    ss = ctx.wrap_socket(s, server_hostname=HOST)
    ss.sendall(req)
    ss.settimeout(8)
    print(ss.recv(400).decode("latin1", "replace"))
    ss.close()
except Exception as e:
    print("remote fail", type(e).__name__, e)
