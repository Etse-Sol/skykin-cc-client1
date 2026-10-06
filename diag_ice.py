import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "docker exec skykin-freeswitch sh -c \"grep -nE 'apply-candidate|ext-rtp-ip|rtp-ip|ws-binding|wss-binding|media_webrtc|candidate-acl|local-network|NDLB|aggressive-nat|rtp-autoadj|dtls|webrtc' /etc/freeswitch/sip_profiles/internal.xml /etc/freeswitch/vars.xml 2>/dev/null\"",
    "docker exec skykin-freeswitch sh -c 'ls /etc/freeswitch/dialplan/default/ | head; echo ---; cat /etc/freeswitch/dialplan/default/00_webrtc_local.xml'",
    "docker exec skykin-freeswitch sh -c \"grep -nE 'media_webrtc|rtp_secure|rtp_advertise|absolute_codec|export' /etc/freeswitch/dialplan/default/*.xml /etc/freeswitch/dialplan/public/*.xml 2>/dev/null\"",
    "docker exec skykin-freeswitch sh -c \"grep -n 'no suitable candidates' /usr/src 2>/dev/null; grep -nE 'candidate|ICE|a=candidate|INCOMPATIBLE' /var/log/freeswitch/freeswitch.log | tail -60\"",
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    print(out[-8000:] if len(out) > 8000 else out)
c.close()
