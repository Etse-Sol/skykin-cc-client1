import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n '81fb0706\|343485e5' /var/log/freeswitch/freeswitch.log | grep -iE 'Opus |Hangup|BYE|MEDIA_TIMEOUT|rtp_timeout|Session-Expires|timer|Auto Changing|bytes in|bytes out|Packet' | tail -40" """,
    r"""docker exec skykin-freeswitch sh -c "grep -nE 'rtp-timeout|media-timeout|session-timeout|enable-timer|minimum-session|rtp_timeout' /etc/freeswitch/sip_profiles/external.xml /etc/freeswitch/sip_profiles/internal.xml /etc/freeswitch/autoload_configs/switch.conf.xml" """,
    r"""docker exec skykin-freeswitch fs_cli -x 'module_exists mod_amr'""",
    r"""docker exec skykin-freeswitch fs_cli -x 'show codec'""",
    r"""docker exec skykin-freeswitch sh -c "ls /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/ | tail" """,
]
for cmd in cmds:
    print("====", cmd[:85])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
