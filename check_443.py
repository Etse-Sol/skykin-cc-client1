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


print("==== listeners ====")
print(run("ss -lntp | grep -E ':443|:8088|:8443|:7443|:80 '"))
print("==== docker ports ====")
print(run("docker ps --format '{{.Names}} {{.Ports}}'"))
print("==== curl 443 ====")
print(run("curl -skI --max-time 8 https://127.0.0.1:443/ | head -20"))
print("==== curl 8088 ====")
print(run("curl -skI --max-time 8 https://127.0.0.1:8088/ | head -15"))
print("==== what owns 443 ====")
print(run("fuser -v 443/tcp 2>&1; lsof -iTCP:443 -sTCP:LISTEN 2>/dev/null | head"))
print("==== ufw ====")
print(run("ufw status | head -40"))
print("==== wss.pem ====")
print(run("ls -l /etc/freeswitch/tls/wss.pem /root/skykin-fs-etc/tls/wss.pem 2>/dev/null; docker exec skykin-freeswitch ls -l /etc/freeswitch/tls/wss.pem 2>/dev/null"))
print("==== openssl 7443 local ====")
print(run("echo | openssl s_client -connect 127.0.0.1:7443 -servername 196.189.236.140 2>/dev/null | openssl x509 -noout -subject -ext subjectAltName -dates 2>/dev/null"))
print("==== openssl 8088 ====")
print(run("echo | openssl s_client -connect 127.0.0.1:8088 -servername 196.189.236.140 2>/dev/null | openssl x509 -noout -subject -ext subjectAltName -dates 2>/dev/null"))
c.close()
