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


print("==== full uuid 4b95019b ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -a '4b95019b' /var/log/freeswitch/freeswitch.log | tail -80\""))

print("==== any 09:1x internal INVITE/dial ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE '2026-08-13 09:1[0-9].*(New Channel|INVITE|destination_number|WRONG_CALL|sofia/internal/10)' /var/log/freeswitch/freeswitch.log | tail -50\""))

c.close()
