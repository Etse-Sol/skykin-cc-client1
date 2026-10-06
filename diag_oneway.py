import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "docker exec skykin-freeswitch fs_cli -x 'show channels'",
    "docker exec skykin-freeswitch sh -c \"grep -E 'sofia/gateway/SIP|sofia/external/\\\\+|AUDIO RTP|Hangup|NO_USER|NORMAL_|bytes|PACKET|rtp_session|SEND|RECV|mute|hold|DTLS|ICE|PCMA|opus|183|200 OK|BYE' /var/log/freeswitch/freeswitch.log | tail -150\"",
    "journalctl -u skykin-ws-sip --since '8 min ago' --no-pager | grep -E 'INVITE|183|200|BYE|480|090|2519' | tail -40",
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    print(out[-14000:] if len(out) > 14000 else out)
c.close()
