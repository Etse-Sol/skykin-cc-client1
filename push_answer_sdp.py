import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
sftp.put(r"C:\Users\hp\skykin-fusionpbx\skykin_ws_sip.py", "/etc/skykin/skykin_ws_sip.py")
sftp.close()
did = "/root/skykin-fs-etc/dialplan/public/01_skykin_did.xml"
cmd = f"""
python3 - <<'PY'
from pathlib import Path
p = Path("{did}")
t = p.read_text()
old = '<action application="export" data="nolocal:include_external_ip=true"/>'
new = old + '\\n      <action application="export" data="nolocal:absolute_codec_string=PCMA"/>'
if "absolute_codec_string=PCMA" not in t:
    if old not in t:
        raise SystemExit("did export not found")
    p.write_text(t.replace(old, new, 1))
    print("did patched")
else:
    print("did already has pcma")
PY
docker exec skykin-freeswitch fs_cli -x reloadxml
systemctl restart skykin-ws-sip
sleep 1
systemctl is-active skykin-ws-sip
CONTACT="[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,absolute_codec_string=PCMA,rtp_advertise_ip=196.189.236.140,include_external_ip=true]"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set contact 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e ${{CONTACT}}user/102@client1.skykin.local"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set status 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e Available"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set state 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e Waiting"
"""
# fix the contact command - bash brace issue
cmd = r"""
python3 - <<'PY'
from pathlib import Path
p = Path("/root/skykin-fs-etc/dialplan/public/01_skykin_did.xml")
t = p.read_text()
old = '<action application="export" data="nolocal:include_external_ip=true"/>'
new = old + '\n      <action application="export" data="nolocal:absolute_codec_string=PCMA"/>'
if "absolute_codec_string=PCMA" not in t:
    if old not in t:
        raise SystemExit("did export not found")
    p.write_text(t.replace(old, new, 1))
    print("did patched")
else:
    print("did already has pcma")
PY
docker exec skykin-freeswitch fs_cli -x reloadxml
systemctl restart skykin-ws-sip
sleep 1
systemctl is-active skykin-ws-sip
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set contact 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e '[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,absolute_codec_string=PCMA,rtp_advertise_ip=196.189.236.140,include_external_ip=true]user/102@client1.skykin.local'"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set status 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e Available"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set state 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e Waiting"
"""
_, o, e = c.exec_command(cmd)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
