import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "docker exec skykin-freeswitch sh -c \"awk '/fd88788b-7bf8-4165-b9f6-b11dc1e16e91/ && /a=candidate|c=IN|m=audio|a=ice|Remote SDP|Local SDP|sdp/ {print}' /var/log/freeswitch/freeswitch.log | tail -80\"",
    "docker exec skykin-freeswitch sh -c 'cat /etc/freeswitch/autoload_configs/acl.conf.xml'",
    "docker exec skykin-freeswitch sh -c 'cat /etc/freeswitch/dialplan/default/00_aa_webrtc_local.xml; echo ====; cat /etc/freeswitch/dialplan/default/00_skykin_webrtc_ua.xml; echo ====; sed -n \"1,40p\" /etc/freeswitch/dialplan/default/00_skykin.xml'",
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
