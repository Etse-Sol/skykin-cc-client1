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


print("==== call 6445d447 (102 outbound that reached dialplan) ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -a '6445d447' /var/log/freeswitch/freeswitch.log | grep -aE 'Dialplan|bridge|lua|INFO|NOTICE|ERR|WARNING|Originate|codec|webrtc|SDP|INVITE' | head -60\""))

print("==== b-leg 1a8697e3 ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -a '1a8697e3' /var/log/freeswitch/freeswitch.log | head -40\""))

print("==== 101 still gone? ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg' | grep -E 'User:|Agent:|Status:'"))

c.close()
