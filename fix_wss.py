import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=30):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print(run(r"""docker exec skykin-web sh -c '
sed -i "s#proxy_pass https://172.22.0.1:7443;#proxy_pass https://10.0.0.93:7443;#" \
  /etc/nginx/sites-available/skykin.conf /etc/nginx/sites-enabled/skykin.conf
nginx -t && nginx -s reload
echo ---
grep -n proxy_pass /etc/nginx/sites-enabled/skykin.conf
'"""))

print("==== wss handshake via 8088 ====")
print(run(r"""curl -sk -o /dev/null -w 'http_code=%{http_code} time=%{time_total}\n' \
  --http1.1 \
  -H 'Connection: Upgrade' \
  -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  https://127.0.0.1:8088/wss/"""))

print("==== nginx errors after reload ====")
print(run("docker exec skykin-web sh -c 'tail -5 /var/log/nginx/error.log'"))

c.close()
