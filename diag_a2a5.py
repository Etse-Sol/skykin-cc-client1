import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=50):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== registrations ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))

print("==== sofia_contact ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia_contact */101@client1.skykin.local'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia_contact */102@client1.skykin.local'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'lua skykin_dest.lua 101 client1.skykin.local'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'lua skykin_dest.lua 102 client1.skykin.local'"))

print("==== last 4 minutes internal calls ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE '2026-08-13 09:1[7-9]|2026-08-13 09:2' /var/log/freeswitch/freeswitch.log | grep -aE 'New Channel sofia/internal|receiving invite|Dialplan:.*destination|EXECUTE.*bridge|Originate|Abandoned|WRONG|USER_NOT|TEMPORARY|Hangup sofia/internal|skykin_dest|webrtc_local' | tail -80\""))

c.close()
