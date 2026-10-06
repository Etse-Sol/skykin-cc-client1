import sys
import time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=50):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== who has 8081 ====")
print(run("ss -lntp | grep -E ':8081|:18081|:8091'; fuser 8081/tcp 2>&1 | head"))

print(run(r"""
systemctl stop skykin-ws-sip
sed -i 's/8081/18081/g' /etc/systemd/system/skykin-ws-sip.service
systemctl daemon-reload
systemctl start skykin-ws-sip
sleep 1
systemctl is-active skykin-ws-sip
ss -lntp | grep 18081
journalctl -u skykin-ws-sip -n 8 --no-pager
"""))

print("==== nginx to 18081 ====")
print(run(r"""
docker exec skykin-web sh -c '
f=/etc/nginx/sites-enabled/skykin.conf
sed -i "s#proxy_pass http://172.22.0.1:8081;#proxy_pass http://172.22.0.1:18081;#" "$f"
sed -i "s#proxy_pass https://172.22.0.1:7443;#proxy_pass http://172.22.0.1:18081;#" "$f"
grep -n proxy_pass "$f"
nginx -t && nginx -s reload
'
ufw allow from 172.16.0.0/12 to any port 18081 proto tcp comment skykin-ws-sip >/dev/null
"""))

print("==== local ws to gateway ====")
print(run(r"""python3 - <<'PY'
import socket
req = (
    "GET / HTTP/1.1\r\nHost: 127.0.0.1:18081\r\nUpgrade: websocket\r\n"
    "Connection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
    "Sec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: sip\r\n\r\n"
).encode()
s = socket.create_connection(("127.0.0.1", 18081), 5)
s.sendall(req)
s.settimeout(5)
print(s.recv(400).decode("latin1", "replace"))
s.close()
PY"""))
c.close()
