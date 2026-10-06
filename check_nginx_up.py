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


print(run("docker exec skykin-web sh -c 'ps aux | grep nginx | grep -v grep; nginx -t; grep proxy_pass /etc/nginx/sites-enabled/skykin.conf'"))
print(run("curl -skI --max-time 8 https://127.0.0.1:8088/ | head -8"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))
print(run("systemctl is-active skykin-ws-sip; ss -lntp | grep 18081"))
c.close()
