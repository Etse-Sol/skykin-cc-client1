import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n 'callcenter\\|INVITE sip:.*102\\|fingerprint\\|Local SDP sofia/internal/102\\|media_webrtc\\|Receiving invite from 10.0.0.93' /var/log/freeswitch/freeswitch.log | tail -40" """,
    "journalctl -u skykin-ws-sip -n 30 --no-pager",
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list'",
    "docker exec skykin-freeswitch sh -c 'ls /etc/freeswitch/autoload_configs/callcenter.conf.xml; grep -n contact /etc/freeswitch/autoload_configs/callcenter.conf.xml | head'",
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
