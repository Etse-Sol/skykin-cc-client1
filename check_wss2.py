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


print("==== nginx proxy_pass live ====")
print(run("docker exec skykin-web grep -n -A8 'location /wss' /etc/nginx/sites-enabled/* /etc/nginx/sites-available/* /etc/nginx/conf.d/* 2>/dev/null | head -60"))

print("==== web -> FS resolve / 7443 ====")
print(run("docker exec skykin-web sh -c 'getent hosts freeswitch; getent hosts skykin-freeswitch; echo ---; (echo >/dev/tcp/freeswitch/7443 && echo tcp_freeswitch_7443_ok) 2>&1; (echo >/dev/tcp/10.0.0.93/7443 && echo tcp_lan_7443_ok) 2>&1; (echo >/dev/tcp/172.22.0.1/7443 && echo tcp_gw_7443_ok) 2>&1'"))

print("==== host listen 7443 ====")
print(run("ss -lnt | grep -E '7443|5066|8088' ; echo ---; docker inspect skykin-freeswitch --format 'nets={{json .NetworkSettings.Networks}} mode={{.HostConfig.NetworkMode}}'"))

print("==== web env ====")
print(run("docker inspect skykin-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E 'WS|TLS|FREESWITCH'"))

print("==== nginx error log ====")
print(run("docker exec skykin-web sh -c 'tail -30 /var/log/nginx/error.log 2>/dev/null; tail -20 /var/log/nginx/error.log.1 2>/dev/null'"))

c.close()
