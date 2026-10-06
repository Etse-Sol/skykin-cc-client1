import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n '0902925776\|+251902925776\|skykin_outbound' /var/log/freeswitch/freeswitch.log | tail -40" """,
    r"""docker exec skykin-freeswitch sh -c "awk '/10:46:20/,/10:46:50/' /var/log/freeswitch/freeswitch.log | grep -E 'New Channel|AUDIO RTP|Hangup|bridge|PCMA|opus|DTLS|ICE|bytes|Packet|jitter|loss|SEND|RECV|rtp_|200 OK|183|BYE|answered|EXECUTE|skykin_outbound|advertise|Remote SDP|Local SDP|c=IN|m=audio|stats|read_codec|write_codec' | tail -160" """,
    r"""docker exec skykin-freeswitch sh -c "ls -lt /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/ 2>/dev/null | head -15" """,
    r"""docker exec skykin-freeswitch fs_cli -x 'sofia status gateway SIP'""",
]
for cmd in cmds:
    print("====", cmd[:85])
    _, o, e = c.exec_command(cmd)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    print(out[-16000:] if len(out) > 16000 else out)
c.close()
