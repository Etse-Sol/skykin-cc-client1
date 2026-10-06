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


print(run("docker exec skykin-freeswitch fs_cli -x 'sofia loglevel all 9'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal siptrace on'"))
print("wait for re-register / ping...")
time.sleep(6)
print(run(r"""docker exec skykin-freeswitch sh -c "grep -aE 'REGISTER sip:|Contact:|\\\\+sip.instance|reg-id|;ob|Supported:|Path:' /var/log/freeswitch/freeswitch.log | tail -50" """))
print("==== check_sync 102 ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal check_sync 102@client1.skykin.local'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal siptrace off'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia loglevel all 0'"))
c.close()
