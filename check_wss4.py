import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=20):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== web -> 10.0.0.93:7443 headers ====")
print(run("docker exec skykin-web timeout 4 curl -skI --max-time 3 https://10.0.0.93:7443/ 2>&1"))

print("==== host -> 8088/wss upgrade ====")
print(run(r"""timeout 4 curl -sk --max-time 3 -D - -o /dev/null \
  --http1.1 \
  -H 'Connection: Upgrade' \
  -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  https://127.0.0.1:8088/wss/ 2>&1"""))

print("==== nginx error tail ====")
print(run("docker exec skykin-web tail -8 /var/log/nginx/error.log"))

c.close()
