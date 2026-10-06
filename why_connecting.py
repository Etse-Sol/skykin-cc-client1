import sys
import time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== gateway ====")
print(run("systemctl is-active skykin-ws-sip; ss -lnt | grep -E '18081|8081'; journalctl -u skykin-ws-sip -n 40 --no-pager"))
print("==== nginx wss ====")
print(run("docker exec skykin-web sh -c 'grep proxy_pass /etc/nginx/sites-enabled/skykin.conf; tail -15 /var/log/nginx/error.log'"))
print("==== regs ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))
print("==== recent sip ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'REGISTER|102@|103@|websocket' /var/log/freeswitch/freeswitch.log | tail -20\""))
c.close()
