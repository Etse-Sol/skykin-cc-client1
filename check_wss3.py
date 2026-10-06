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


print("==== FS listen 7443/5066 ====")
print(run("docker exec skykin-freeswitch sh -c 'ss -lnt 2>/dev/null || netstat -lnt' | grep -E '7443|5066|5060|5080|8088'"))

print("==== host listen ====")
print(run("ss -lnt | grep -E '7443|5066|8088|8090' || true"))

print("==== web hosts + nginx wss ====")
print(run("docker exec skykin-web sh -c 'grep -E \"freeswitch|wss|7443\" /etc/hosts /etc/nginx/sites-available/skykin.conf /etc/nginx/sites-enabled/skykin.conf 2>/dev/null'"))

print("==== curl 10.0.0.93:7443 from web (3s) ====")
print(run("docker exec skykin-web sh -c 'timeout 3 curl -skI https://10.0.0.93:7443/ 2>&1 | head -15; echo EXIT:$?'"))

print("==== curl 127.0.0.1:7443 on host (3s) ====")
print(run("timeout 3 curl -skI https://127.0.0.1:7443/ 2>&1 | head -15; echo EXIT:$?"))

c.close()
