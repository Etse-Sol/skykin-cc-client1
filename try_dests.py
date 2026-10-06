import sys
import time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=35):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== wss cert / established 7443 ====")
print(run("docker exec skykin-freeswitch grep -n 'wss-cert\\|wss-key\\|tls-cert' /etc/freeswitch/sip_profiles/internal.xml | head -20"))
print(run("ss -tnp | grep ':7443' | head -15"))

contact = run("docker exec skykin-freeswitch fs_cli -x 'sofia_contact */103@client1.skykin.local'").strip()
print("contact:", contact)

dests = [
    "{media_webrtc=true,rtp_secure_media=optional}sofia/internal/sip:103@client1.skykin.local;transport=wss",
    "{media_webrtc=true,rtp_secure_media=optional}sofia/internal/sip:103@client1.skykin.local;transport=wss;fs_path=sip:10.0.0.93:7443;transport=wss",
]

# Strip fs_path from live contact
raw = contact
if raw.startswith("sofia/internal/"):
    raw = raw[len("sofia/internal/"):]
stripped = raw.split(";fs_path=")[0].split(";fs_nat=")[0]
dests.append("{media_webrtc=true,rtp_secure_media=optional}sofia/internal/" + stripped)

for i, d in enumerate(dests):
    print(f"\n==== try {i}: {d[:110]} ====")
    run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal siptrace on'")
    run("docker exec skykin-freeswitch fs_cli -x \"bgapi originate " + d.replace('"', '') + " &park\"")
    time.sleep(1.5)
    print(run("docker exec skykin-freeswitch sh -c \"grep -aE '2026-08-13 09:2[6-9]|2026-08-13 09:3' /var/log/freeswitch/freeswitch.log | grep -aE 'INVITE sip:|SIP/2.0 50|SIP/2.0 18|terminated|sending invite' | tail -12\""))
    run("docker exec skykin-freeswitch fs_cli -x 'hupall NORMAL_CLEARING'")
    run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal siptrace off'")

c.close()
