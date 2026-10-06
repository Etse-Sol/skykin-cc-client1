import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -cE 'a=sendonly|a=recvonly|a=inactive|a=sendrecv|a=rtcp-mux' /var/log/freeswitch/freeswitch.log" """,
    r"""docker exec skykin-freeswitch sh -c "grep -nE 'a=sendonly|a=recvonly|a=inactive' /var/log/freeswitch/freeswitch.log | tail -40" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n 'ede91b4c' /var/log/freeswitch/freeswitch.log | grep -iE 'sendonly|recvonly|sendrecv|rtcp-mux|m=audio|c=IN IP4|Local SDP|Remote SDP|Secure|DTLS' | tail -60" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n 'b9529515' /var/log/freeswitch/freeswitch.log | grep -iE 'sendonly|recvonly|sendrecv|rtcp-mux|m=audio|c=IN IP4|Local SDP|Remote SDP' | tail -40" """,
]
for cmd in cmds:
    print("====", cmd[:100])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
