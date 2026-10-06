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
    r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php",
    "/opt/call-center-deployement/call-center/app/agent_dashboard/index.php",
)
sftp.put(
    r"C:\Users\hp\skykin-fusionpbx\skykin_ws_sip.py",
    "/etc/skykin/skykin_ws_sip.py",
)
sftp.put(
    r"C:\Users\hp\skykin-fusionpbx\fix_inbound_webrtc.py",
    "/tmp/fix_inbound_webrtc.py",
)
sftp.close()

cmds = r"""
python3 /tmp/fix_inbound_webrtc.py
python3 - <<'PY'
from pathlib import Path
old = "api_on_answer=sched_api +1 none uuid_media_reneg ${bleg_uuid},"
old2 = "api_on_answer=sched_api +1 none uuid_media_reneg ${uuid},"
n = 0
for p in Path("/root/skykin-fs-etc/dialplan").rglob("*.xml"):
    t = p.read_text()
    if old in t or old2 in t or "uuid_media_reneg" in t:
        t = t.replace(old, "").replace(old2, "")
        t = t.replace("api_on_answer=sched_api +1 none uuid_media_reneg ${bleg_uuid}", "")
        t = t.replace("api_on_answer=sched_api +1 none uuid_media_reneg ${uuid}", "")
        p.write_text(t)
        n += 1
        print("stripped reneg", p)
print("files patched", n)
PY
docker exec skykin-freeswitch fs_cli -x reloadxml
systemctl restart skykin-ws-sip
sleep 1
systemctl is-active skykin-ws-sip
echo '==== reneg left ===='
grep -n uuid_media_reneg /root/skykin-fs-etc/dialplan/default/00_skykin.xml \
  /root/skykin-fs-etc/dialplan/01_skykin_client1.skykin.local.xml \
  /root/skykin-fs-etc/dialplan/public/01_skykin_did.xml || echo none
echo '==== index stamp ===='
grep -n '20260813j\|opusMonoFmtpModifier' \
  /opt/call-center-deployement/call-center/app/agent_dashboard/index.php | head
"""
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
