import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=45):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== listeners 8088 / 7443 / 5066 ====")
print(run("ss -lntup | grep -E ':8088|:7443|:5066|:443|:8090' || netstat -lntup 2>/dev/null | grep -E '8088|7443|5066'"))

print("==== nginx wss in skykin-web ====")
print(run("docker exec skykin-web sh -c 'grep -n -A20 -E \"wss|7443|5066|proxy_pass\" /etc/nginx/conf.d/*.conf /etc/nginx/nginx.conf 2>/dev/null | head -80'"))

print("==== FS sofia status (wss) ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | grep -iE 'WSS|WS-BIND|BIND-URL|TLS'"))

print("==== curl https / wss upgrade locally ====")
print(run("curl -skI https://127.0.0.1:8088/ 2>&1 | head -20"))
print(run("curl -skI http://127.0.0.1:8088/ 2>&1 | head -15"))
print(run("curl -skI -H 'Connection: Upgrade' -H 'Upgrade: websocket' https://127.0.0.1:8088/wss/ 2>&1 | head -25"))

print("==== web container ports / cert ====")
print(run("docker port skykin-web"))
print(run("docker exec skykin-web sh -c 'ls -l /etc/nginx/ssl /etc/ssl/certs 2>/dev/null; openssl x509 -in /etc/nginx/ssl/fullchain.pem -noout -subject -dates -ext subjectAltName 2>/dev/null; openssl x509 -in /etc/ssl/certs/nginx.crt -noout -subject -dates -ext subjectAltName 2>/dev/null'"))

print("==== recent nginx / FS wss errors ====")
print(run("docker logs skykin-web --tail 40 2>&1 | tail -40"))
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'wss|7443|handshake|SSL' /var/log/freeswitch/freeswitch.log | tail -20\""))

c.close()
