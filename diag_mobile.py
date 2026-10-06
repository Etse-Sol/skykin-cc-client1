import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "docker exec skykin-freeswitch fs_cli -x 'sofia status gateway SIP'",
    "docker exec skykin-freeswitch sh -c 'cat /etc/freeswitch/dialplan/default/00_skykin.xml'",
    "docker exec skykin-freeswitch sh -c 'ls /etc/freeswitch/dialplan/default/; echo ---; cat /etc/freeswitch/dialplan/default/00_ethio_mobile.xml 2>/dev/null'",
    "docker exec skykin-freeswitch sh -c \"grep -E 'sofia/gateway/SIP|INVITE sip:\\\\+|180 Ringing|183 Session|200 OK|480|486|487|503|403|404|488|NO_USER|NORMAL_|DESTINATION|Originate|hangup_cause|sip_hangup' /var/log/freeswitch/freeswitch.log | tail -120\"",
    "journalctl -u skykin-ws-sip --since '8 min ago' --no-pager | tail -80",
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    print(out[-12000:] if len(out) > 12000 else out)
c.close()
