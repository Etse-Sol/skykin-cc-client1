import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
uid = "587bb95f-7331-45b9-b581-7bc753217db0"
cmds = [
    f"""docker exec skykin-freeswitch sh -c "grep -n '{uid}' /var/log/freeswitch/freeswitch.log | grep -iE 'Local SDP|Remote SDP|rtcp-mux|sendrecv|sendonly|INVITE|re-INVITE|media_reneg|RENEG|Secure|DTLS|m=audio|c=IN IP4|Hangup|answered|BYE|uuid_media|EXECUTE|bridge' | head -80" """,
    f"""docker exec skykin-freeswitch sh -c "grep -n 'uuid_media_reneg\\|{uid}' /var/log/freeswitch/freeswitch.log | grep -iE 'media_reneg|RENEG|Sending INVITE|re-invite|UPDATE' | tail -30" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n 'sofia/external/+251902925776' /var/log/freeswitch/freeswitch.log | tail -20" """,
]
for cmd in cmds:
    print("====", cmd[:100])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
