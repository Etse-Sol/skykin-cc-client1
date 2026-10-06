import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "docker exec skykin-freeswitch sh -c \"grep -n '0902925776\\|251902925776\\|+251902925776\\|sofia/gateway/SIP' /var/log/freeswitch/freeswitch.log | tail -80\"",
    "docker exec skykin-freeswitch sh -c \"awk '/10:40:57/,/10:41:06/' /var/log/freeswitch/freeswitch.log | grep -E 'INVITE|183|480|200|hangup|Originate|Dialplan|sofia/gateway|Remote SDP|Local SDP|c=IN|m=audio|Cause|NO_USER|EXECUTE|bridge|ethio|skykin_outbound|destination' | tail -100\"",
    "docker exec skykin-freeswitch sh -c 'cat /etc/freeswitch/sip_profiles/external/SIP.xml'",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status profile external'",
]
for cmd in cmds:
    print("====", cmd[:85])
    _, o, e = c.exec_command(cmd)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    print(out[-14000:] if len(out) > 14000 else out)
c.close()
