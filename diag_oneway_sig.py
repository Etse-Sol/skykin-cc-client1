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


print("==== channels ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'show channels concise'"))
print("==== regs ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))
print("==== last 102/103 ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'Processing 102|Processing 103|180 Ringing|200 OK|ACK|BRIDGE|answered|CS_EXCHANGE|hangup' /var/log/freeswitch/freeswitch.log | tail -40\""))
print("==== gateway ====")
print(run("journalctl -u skykin-ws-sip -n 60 --no-pager"))
c.close()
