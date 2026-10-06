import sys
import time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=45):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print(run(r"""
docker exec skykin-freeswitch sh -c '
f=/etc/freeswitch/sip_profiles/internal.xml
# NDLB-tls-connectile-dysfunction injects fs_path=nginx-ephemeral, and
# originate then opens a NEW WSS to that port (not a listener) -> 503.
sed -i "s#<param name=\"sip-force-contact\" value=\"NDLB-tls-connectile-dysfunction\"/>#<param name=\"sip-force-contact\" value=\"\"/>#" "$f"
sed -i "s#<param name=\"apply-nat-acl\" value=\"nat.auto\"/>#<param name=\"apply-nat-acl\" value=\"none\"/>#" "$f"
grep -n "sip-force-contact\|apply-nat-acl\|enable-rfc-5626" "$f"
'
"""))

print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal restart'"))
print("waiting for agents to re-register...")
for i in range(6):
    time.sleep(3)
    regs = run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'")
    users = [ln for ln in regs.splitlines() if ln.strip().startswith("User:")]
    print(f"  {i}: {users}")
    if any("102@" in u or "103@" in u for u in users):
        print(regs)
        break

print("==== sofia_contact 103 ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia_contact */103@client1.skykin.local'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia_contact */102@client1.skykin.local'"))

print("==== originate 103 ====")
print(run("docker exec skykin-freeswitch fs_cli -x \"bgapi originate {media_webrtc=true,rtp_secure_media=optional,originate_timeout=8}sofia/internal/103@client1.skykin.local &park\""))
time.sleep(3)
print(run("docker exec skykin-freeswitch fs_cli -x 'show channels concise'"))
print(run("docker exec skykin-freeswitch sh -c \"grep -aE '2026-08-13 09:3[5-9]|2026-08-13 09:4' /var/log/freeswitch/freeswitch.log | grep -aE 'sending invite|terminated|180|200|RINGING|TEMPORARY' | tail -15\""))
run("docker exec skykin-freeswitch fs_cli -x 'hupall NORMAL_CLEARING'")
c.close()
