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


print("==== vars ext-rtp / domain ====")
print(run("docker exec skykin-freeswitch grep -n 'external_rtp_ip\\|external_sip_ip\\|domain=' /etc/freeswitch/vars.xml | head -20"))

print("==== test originate user/103 ====")
# Don't ring the agent for long — 8s then kill.
run("docker exec skykin-freeswitch fs_cli -x \"bgapi originate {media_webrtc=true,rtp_secure_media=optional,originate_timeout=8}user/103@client1.skykin.local &playback(/usr/share/freeswitch/sounds/music/8000/suite-espanola-op-47-leyenda.wav)\"")
time.sleep(3)
print(run("docker exec skykin-freeswitch fs_cli -x 'show channels'"))
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'originate|user/103|TEMPORARY|WRONG|INVITE|sending invite' /var/log/freeswitch/freeswitch.log | tail -25\""))
run("docker exec skykin-freeswitch fs_cli -x 'hupall NORMAL_CLEARING'")

print("==== wss_contact.lua ====")
print(run("docker exec skykin-freeswitch cat /usr/share/freeswitch/scripts/wss_contact.lua"))

c.close()
