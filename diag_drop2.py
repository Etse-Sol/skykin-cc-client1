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

print("==== last 8 min internal ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE '2026-08-13 09:3[0-9]' /var/log/freeswitch/freeswitch.log | grep -aE 'New Channel sofia/internal|Processing .*->|EXECUTE.*bridge|sending invite|terminated|Originate|TEMPORARY|USER_NOT|Hangup sofia/internal|180 Ringing|SIP/2.0 180|SIP/2.0 200|DTLS' | tail -70\""))

c.close()
