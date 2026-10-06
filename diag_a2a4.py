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


print("==== 09:14:08 context (no uuid filter) ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -an '2026-08-13 09:14:0' /var/log/freeswitch/freeswitch.log | grep -iE '407|401|PRACK|100rel|SDP|INVITE|detach|auth|warning|error|Abandoned' | head -40\""))

print("==== internal 100rel / late-neg ====")
print(run("docker exec skykin-freeswitch grep -n 'enable-100rel\\|inbound-late\\|inbound-codec\\|liberal-dtmf\\|ws-binding\\|wss-binding' /etc/freeswitch/sip_profiles/internal.xml"))

print("==== sip trace last invite? ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -a 'recv 2.*INVITE\\|send 1.*407\\|send 1.*100\\|send 1.*200' /var/log/freeswitch/freeswitch.log | tail -20\""))

c.close()
