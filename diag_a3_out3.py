import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "sed -n '248125,248320p' /var/log/freeswitch/freeswitch.log | grep -E 'EXECUTE|DTLS|ICE|Secure|answer|bridge|Hangup|fingerprint|READY|WARNING|ERR'" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n 'fe975d03' /var/log/freeswitch/freeswitch.log | grep -iE 'DTLS|ICE|Secure|bridge|gateway|WARNING|ERR|answer|ACK'" """,
    "cat /root/skykin-fs-etc/directory/default/103.xml",
    "cat /root/skykin-fs-etc/directory/default/102.xml",
    r"""docker exec skykin-freeswitch sh -c "sed -n '247897,248130p' /var/log/freeswitch/freeswitch.log | grep -E 'Dialplan:|Regex|skykin_outbound|Action'" """,
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
