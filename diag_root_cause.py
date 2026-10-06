import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "ls -lt /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/*.wav | head -8" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n 'sofia/internal/101@\\|MicroSIP\\|101@client1\\|AUDIO RTP.*101\\|Hangup sofia/internal/101\\|bridge.*SIP/' /var/log/freeswitch/freeswitch.log | tail -40" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n 'New Channel sofia/external/anonymous\\|New Channel sofia/internal/101\\|New Channel sofia/internal/102\\|New Channel sofia/internal/103' /var/log/freeswitch/freeswitch.log | tail -20" """,
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
