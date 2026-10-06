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


print("==== regs ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))
print("==== last calls ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'Processing 10[0-9].*10[0-9]|sending invite|terminated|TEMPORARY|NO_USER|USER_NOT|hangup complete|Cause:' /var/log/freeswitch/freeswitch.log | tail -40\""))
print("==== webrtc dest ====")
print(run("docker exec skykin-freeswitch cat /etc/freeswitch/dialplan/default/00_webrtc_local.xml"))
print(run("docker exec skykin-freeswitch cat /usr/share/freeswitch/scripts/skykin_dest.lua"))
print("==== rfc5626 ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -n '5626\\|force-contact\\|wss-binding' /etc/freeswitch/sip_profiles/internal.xml\""))
c.close()
