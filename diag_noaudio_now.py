import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "journalctl -u skykin-ws-sip -n 35 --no-pager",
    r"""docker exec skykin-freeswitch sh -c "ls -lt /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/*.wav | head -4" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n 'sofia/internal/102\\|DTLS\\|ICE\\|fingerprint\\|AUDIO RTP\\|Hangup\\|answered\\|200 OK\\|BRIDGE' /var/log/freeswitch/freeswitch.log | tail -50" """,
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
