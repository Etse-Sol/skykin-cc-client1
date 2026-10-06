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


contact = run("docker exec skykin-freeswitch fs_cli -x 'sofia_contact */103@client1.skykin.local'").strip()
print("CONTACT", contact)
stripped = contact
for p in (";fs_path=", ";fs_nat="):
    if p in stripped:
        # cut from param to next ; or end
        i = stripped.find(p)
        j = stripped.find(";", i + 1)
        stripped = stripped[:i] + (stripped[j:] if j != -1 else "")
print("STRIPPED", stripped)

tests = [
    ("user", "{media_webrtc=true,rtp_secure_media=optional,originate_timeout=5}user/103@client1.skykin.local"),
    ("sofia-user", "{media_webrtc=true,rtp_secure_media=optional,originate_timeout=5}sofia/internal/103@client1.skykin.local"),
    ("stripped", "{media_webrtc=true,rtp_secure_media=optional,originate_timeout=5}" + stripped),
    ("invalid-ob", "{media_webrtc=true,rtp_secure_media=optional,originate_timeout=5}sofia/internal/sip:103@client1.skykin.local;transport=wss"),
]

for name, dest in tests:
    print(f"\n==== {name} ====")
    print(run(f'docker exec skykin-freeswitch fs_cli -x "bgapi originate {dest} &park"'))
    time.sleep(2.2)
    chans = run("docker exec skykin-freeswitch fs_cli -x 'show channels count'")
    print(chans)
    print(run("docker exec skykin-freeswitch sh -c \"grep -a 'sending invite\\|terminated\\|RINGING\\|180 Ringing\\|TEMPORARY' /var/log/freeswitch/freeswitch.log | tail -6\""))
    run("docker exec skykin-freeswitch fs_cli -x 'hupall NORMAL_CLEARING'")
    time.sleep(0.4)

print("==== internal bind ====")
print(run(r"""docker exec skykin-freeswitch sh -c "grep -nE 'sip-port|disable-tcp|ws-binding|wss-binding|sip-ip' /etc/freeswitch/sip_profiles/internal.xml | head -30" """))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | head -40"))
c.close()
