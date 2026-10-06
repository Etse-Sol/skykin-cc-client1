import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
uid = "e76ff3f9-c764-401e-ad82-2b700e1e3b32"
cmds = [
    f"""docker exec skykin-freeswitch sh -c "sed -n '231180,231290p' /var/log/freeswitch/freeswitch.log" """,
    f"""docker exec skykin-freeswitch sh -c "grep -n '{uid}' /var/log/freeswitch/freeswitch.log | grep -iE 'Local SDP|Remote SDP|rtcp-mux|PRACK|100rel|Require|m=audio|c=IN IP4|Secure|DTLS|Hangup|answered|BYE|codec'" """,
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
