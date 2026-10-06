import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    username="root",
    password="Pass@1234",
    timeout=25,
    allow_agent=False,
    look_for_keys=False,
)
sftp = c.open_sftp()
sftp.put(
    r"C:\Users\hp\skykin-fusionpbx\fix_inbound_webrtc.py",
    "/tmp/fix_inbound_webrtc.py",
)
sftp.close()

sip_contact = "[leg_timeout=30]user/101@client1.skykin.local"
web_contact = (
    "[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,"
    "rtp_advertise_ip=196.189.236.140,include_external_ip=true]"
)
cmds = f"""
python3 /tmp/fix_inbound_webrtc.py
python3 - <<'PY'
from pathlib import Path
p = Path("/root/skykin-fs-etc/autoload_configs/callcenter.conf.xml")
t = p.read_text()
old = '<param name="moh-sound" value="$${{hold_music}}"/>'
new = '<param name="moh-sound" value=""/>'
if old in t:
    p.write_text(t.replace(old, new))
    print("moh-sound cleared in callcenter.conf.xml")
elif 'moh-sound' in t:
    import re
    t2, n = re.subn(r'<param name="moh-sound" value="[^"]*"/>',
                    '<param name="moh-sound" value=""/>', t, count=1)
    p.write_text(t2)
    print("moh-sound rewritten", n)
else:
    print("moh-sound not found")
PY
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c \\
  "UPDATE v_call_center_queues SET queue_moh_sound = '' WHERE queue_extension = '8000';" \\
  2>/dev/null || echo "no fusionpbx queue row (ok)"
docker exec skykin-freeswitch fs_cli -x reloadxml
docker exec skykin-freeswitch fs_cli -x "callcenter_config queue reload 8000@client1.skykin.local"
docker exec skykin-freeswitch fs_cli -x \\
  "callcenter_config agent set contact 64c5f323-cd40-48ef-a97f-22d546be8b57 '{sip_contact}'"
docker exec skykin-freeswitch fs_cli -x \\
  "callcenter_config agent set contact 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e '{web_contact}user/102@client1.skykin.local'"
docker exec skykin-freeswitch fs_cli -x \\
  "callcenter_config agent set contact cd794b4f-f54e-4110-ba5d-537a034c243c '{web_contact}user/103@client1.skykin.local'"
echo '==== DID ===='
cat /root/skykin-fs-etc/dialplan/public/01_skykin_did.xml
echo '==== MOH ===='
grep moh-sound /root/skykin-fs-etc/autoload_configs/callcenter.conf.xml
echo '==== QUEUE ===='
docker exec skykin-freeswitch fs_cli -x "callcenter_config queue list" | head -3
echo '==== AGENTS ===='
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent list" | cut -d'|' -f1,5,6
"""
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
