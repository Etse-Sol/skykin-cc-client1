import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== trunk ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status gateway SIP'"))
print("==== regs ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))
print("==== bind ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | grep -E 'BIND|SIP-IP|RTP-IP|REGISTRATIONS'"))
print("==== nginx ====")
print(run("docker exec skykin-web grep proxy_pass /etc/nginx/sites-enabled/skykin.conf"))
print("==== dialplan ====")
print(run("docker exec skykin-freeswitch sh -c 'echo === webrtc ===; cat /etc/freeswitch/dialplan/default/00_webrtc_local.xml; echo === skykin head ===; head -80 /etc/freeswitch/dialplan/default/00_skykin.xml; echo === lua ===; cat /usr/share/freeswitch/scripts/skykin_dest.lua'"))
print("==== gateway svc ====")
print(run("systemctl is-active skykin-ws-sip || true"))
c.close()
