import sys
import time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== 5626 / wss params ====")
print(run("docker exec skykin-freeswitch grep -n '5626\\|wss-binding\\|ws-binding\\|rfc' /etc/freeswitch/sip_profiles/internal.xml | head -30"))

print("==== siptrace one originate ====")
run("docker exec skykin-freeswitch fs_cli -x 'sofia global siptrace on'")
run("docker exec skykin-freeswitch fs_cli -x \"bgapi originate {media_webrtc=true,rtp_secure_media=optional,originate_timeout=5}sofia/internal/103@client1.skykin.local &park\"")
time.sleep(2)
run("docker exec skykin-freeswitch fs_cli -x 'hupall NORMAL_CLEARING'")
run("docker exec skykin-freeswitch fs_cli -x 'sofia global siptrace off'")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'recv [0-9]+ bytes|send [0-9]+ bytes|SIP/2.0 503|INVITE sip:|terminated' /var/log/freeswitch/freeswitch.log | tail -40\""))

c.close()
