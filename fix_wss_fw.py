import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=25):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== INPUT policy / 7443 rules ====")
print(run("iptables -L INPUT -n -v --line-numbers | head -40"))
print(run("iptables -L DOCKER-USER -n -v --line-numbers 2>/dev/null | head -20"))

# Allow Docker / RFC1918 to the host-networked FreeSWITCH WSS listener.
print(run("iptables -C INPUT -p tcp -s 172.16.0.0/12 --dport 7443 -j ACCEPT 2>/dev/null || "
          "iptables -I INPUT 1 -p tcp -s 172.16.0.0/12 --dport 7443 -j ACCEPT"))
print(run("iptables -C INPUT -p tcp -s 172.16.0.0/12 --dport 5066 -j ACCEPT 2>/dev/null || "
          "iptables -I INPUT 1 -p tcp -s 172.16.0.0/12 --dport 5066 -j ACCEPT"))
print("  added INPUT accept for 7443/5066 from docker nets")

# Point nginx at the bridge gateway (same net as the web container) now that it is allowed.
print(run(r"""docker exec skykin-web sh -c '
sed -i "s#proxy_pass https://10.0.0.93:7443;#proxy_pass https://172.22.0.1:7443;#" \
  /etc/nginx/sites-available/skykin.conf /etc/nginx/sites-enabled/skykin.conf
nginx -t && nginx -s reload
grep proxy_pass /etc/nginx/sites-enabled/skykin.conf
'"""))

print("==== web -> 172.22.0.1:7443 ====")
print(run("docker exec skykin-web timeout 4 curl -skI --max-time 3 https://172.22.0.1:7443/ 2>&1; echo EXIT:$(echo $?)"))

print("==== host 8088/wss ====")
print(run(r"""timeout 4 curl -sk --max-time 3 -D - -o /dev/null \
  --http1.1 \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  https://127.0.0.1:8088/wss/ 2>&1"""))

c.close()
