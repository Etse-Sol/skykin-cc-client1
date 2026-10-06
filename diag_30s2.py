import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n '10:53:4[0-9]\|10:53:5\|10:54:0\|10:54:1\|10:54:2' /var/log/freeswitch/freeswitch.log | grep -E 'New Channel|Hangup|AUDIO RTP|183|200|BYE|MEDIA|TIMEOUT|DTLS|ICE|opus|PCMA|c=IN|m=audio|Remote SDP|Local SDP|late|ignore_early|session timer|Session-Expires|rtp_timeout|MEDIA_TIMEOUT' | tail -120" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n 'def635aa\|c286f88e\|10:53:45\|10:54:50' /var/log/freeswitch/freeswitch.log | grep -E 'New Channel sofia/internal/102|New Channel sofia/external' | tail -20" """,
]
for cmd in cmds:
    print("====", cmd[:85])
    _, o, e = c.exec_command(cmd)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    print(out[-16000:] if len(out) > 16000 else out)
c.close()
