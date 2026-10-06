import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n 'ede91b4c\|b9529515' /var/log/freeswitch/freeswitch.log | grep -E 'Set Codec|AUDIO RTP|Local SDP|Remote SDP|m=audio|c=IN|rtpmap|answered|Hangup|resampler|Opus |PCMA|AMR|ssrc|Auto Changing' | head -80" """,
    r"""docker exec skykin-freeswitch sh -c "awk '/b9529515/ && /Local SDP/,/Standard INIT/' /var/log/freeswitch/freeswitch.log | head -25" """,
    r"""docker exec skykin-freeswitch sh -c "awk '/b9529515/ && /Remote SDP/,/Pre-Answer|has been answered/' /var/log/freeswitch/freeswitch.log | head -30" """,
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace")[:9000])
c.close()
