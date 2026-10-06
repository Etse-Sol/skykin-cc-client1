import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n '4257d123\\|29004616' /var/log/freeswitch/freeswitch.log | grep -iE 'SDP|m=audio|m=video|BUNDLE|sendonly|recvonly|inactive|sendrecv|PCMA|opus|Secure|codec|read=|write=|Packet|hangup complete|bytes|jitter|silence|CN |payload' | tail -80" """,
    r"""docker exec skykin-freeswitch sh -c "awk '/4257d123/ && /Local SDP|Remote SDP|a=group|m=audio|m=video|a=send|a=recv|a=inactive|a=rtpmap|a=fingerprint|a=ice|c=IN/{print}' /var/log/freeswitch/freeswitch.log | tail -120" """,
    r"""docker exec skykin-freeswitch sh -c "sed -n '237850,238140p' /var/log/freeswitch/freeswitch.log | grep -E 'm=audio|m=video|a=group|a=send|a=recv|a=inactive|a=rtpmap|c=IN|a=fingerprint|a=ice|Local SDP|Remote SDP|v=0|PCMA|opus'" """,
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
