import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "docker exec skykin-freeswitch cat /etc/freeswitch/autoload_configs/amr.conf.xml",
    "docker exec skykin-freeswitch sh -c 'grep -n amrwb /etc/freeswitch/autoload_configs/modules.conf.xml'",
    "docker exec skykin-freeswitch sh -c \"grep -A20 'Remote SDP' /var/log/freeswitch/freeswitch.log | grep -E 'AMR|fmtp|rtpmap|a=' | tail -40\"",
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace")[:4000])
c.close()
