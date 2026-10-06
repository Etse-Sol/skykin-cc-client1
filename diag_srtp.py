import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n 'b9529515' /var/log/freeswitch/freeswitch.log | grep -iE 'Secure|DTLS|SAVP|webrtc|rtp_secure|crypto'" """,
    "docker exec skykin-freeswitch cat /etc/freeswitch/dialplan/default/00_skykin_webrtc_ua.xml",
    "docker exec skykin-freeswitch sh -c 'grep -n rtcp-mux /etc/freeswitch/sip_profiles/external.xml /etc/freeswitch/sip_profiles/internal.xml'",
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
