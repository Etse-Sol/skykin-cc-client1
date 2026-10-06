import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n '465d02de\|f16b094e' /var/log/freeswitch/freeswitch.log | grep -E 'New Channel|Set Codec|AUDIO RTP|Local SDP|Remote SDP|Hangup|answered|AMR|PCMA|c=IN|m=audio|rtpmap' | head -80" """,
    r"""docker exec skykin-freeswitch sh -c "awk '/f16b094e/ && /Local SDP/,/f16b094e.*Standard INIT/' /var/log/freeswitch/freeswitch.log | head -40" """,
    r"""docker exec skykin-freeswitch sh -c "awk '/f16b094e/ && /Remote SDP/,/Pre-Answer|has been answered/' /var/log/freeswitch/freeswitch.log | head -50" """,
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace")[:8000])
c.close()
