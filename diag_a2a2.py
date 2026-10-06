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


print("==== around WRONG_CALL_STATE / last 8 min ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE '2026-08-13 09:1[3-9].*(INVITE|Dialplan:|bridge|WRONG|TEMPORARY|user/|sofia_contact|destination_number|Hangup sofia/internal)' /var/log/freeswitch/freeswitch.log | tail -80\""))

print("==== aa webrtc still old? ====")
print(run("docker exec skykin-freeswitch cat /etc/freeswitch/dialplan/default/00_aa_webrtc_local.xml"))

print("==== sofia_contact ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia_contact */101@client1.skykin.local'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia_contact */102@client1.skykin.local'"))

c.close()
