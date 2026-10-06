import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "docker inspect skykin-freeswitch --format 'net={{.HostConfig.NetworkMode}} pid={{.State.Pid}}'",
    "ip -4 addr show | sed -n '1,80p'",
    r"""docker exec skykin-freeswitch sh -c "sed -n '229950,230120p' /var/log/freeswitch/freeswitch.log" """,
    "ls -l /root/skykin-fs-etc/dialplan/client1.skykin.local/",
    "docker exec skykin-freeswitch ls -l /etc/freeswitch/dialplan/client1.skykin.local/",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status gateway SIP'",
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
