import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n 'f16b094e\|10:58:53\|10:58:54\|10:59:0\|10:59:2' /var/log/freeswitch/freeswitch.log | grep -E 'New Channel|Local SDP|Remote SDP|AUDIO RTP|Set Codec|AMR|PCMA|Hangup|183|200|BYE|Opus |c=IN|m=audio|rtpmap|fmtp|answered|Auto Changing' | tail -100" """,
    r"""docker exec skykin-freeswitch sh -c "ls -lt /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/*.wav | head -5" """,
]
for cmd in cmds:
    print("====", cmd[:85])
    _, o, e = c.exec_command(cmd)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    print(out[-18000:] if len(out) > 18000 else out)
c.close()
