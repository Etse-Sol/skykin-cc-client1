import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "echo '==== public dp ===='",
    "docker exec skykin-freeswitch sh -c 'ls -l /etc/freeswitch/dialplan/public/; echo ---; cat /etc/freeswitch/dialplan/public/*.xml 2>/dev/null | head -120'",
    "echo '==== inbound host ===='",
    "ls -l /root/skykin-fs-etc/dialplan/public/ 2>/dev/null; cat /root/skykin-fs-etc/dialplan/public/*.xml 2>/dev/null | head -120",
    "echo '==== outbound uuid ===='",
    r"""docker exec skykin-freeswitch sh -c "grep -n '427c34c5-557c-48a8-8b24-0b2517b069c2' /var/log/freeswitch/freeswitch.log | grep -iE 'bridge|Hangup|answered|Local SDP|Remote SDP|uuid_media|RENEG|BYE|m=audio|c=IN IP4|rtcp-mux|Invalid rtcp|AUDIO RTP' | head -60" """,
    "echo '==== inbound uuid ===='",
    r"""docker exec skykin-freeswitch sh -c "grep -n 'fbd06d8c-9475-49cd-8225-88a0b050d396' /var/log/freeswitch/freeswitch.log | grep -iE 'receiving|INVITE|destination|Dialplan: sofia|EXECUTE|transfer|callcenter|Hangup|context|8000|251111' | head -50" """,
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
