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


print("==== originate sofia/internal/103@domain ====")
print(run("docker exec skykin-freeswitch fs_cli -x \"bgapi originate {media_webrtc=true,rtp_secure_media=optional,originate_timeout=12}sofia/internal/103@client1.skykin.local &playback(silence_stream://8000)\""))
time.sleep(4)
print(run("docker exec skykin-freeswitch fs_cli -x 'show channels concise'"))
print(run("docker exec skykin-freeswitch sh -c \"grep -a '2026-08-13 09:2[1-9]' /var/log/freeswitch/freeswitch.log | grep -aE 'sending invite|TEMPORARY|RINGING|183|180|200 OK|CS_CONSUME|Hangup sofia/internal/103|sofia/internal/103@' | tail -20\""))
run("docker exec skykin-freeswitch fs_cli -x 'hupall NORMAL_CLEARING'")

c.close()
