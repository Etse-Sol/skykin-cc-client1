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
sftp.close()

cmds = r"""
python3 - <<'PY'
from pathlib import Path
for p in [
    Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml"),
    Path("/root/skykin-fs-etc/dialplan/01_skykin_client1.skykin.local.xml"),
]:
    t = p.read_text()
    t2 = t.replace("ignore_early_media=false", "ignore_early_media=true")
    t2 = t2.replace('      <action application="pre_answer"/>\n', "")
    t2 = t2.replace('      <action application="sleep" data="400"/>\n', "")
    if t2 != t:
        p.write_text(t2)
        print("patched", p)
    else:
        print("no change", p)
    print("---", p.name, "outbound bits ---")
    for i, line in enumerate(t2.splitlines(), 1):
        if "pre_answer" in line or "ignore_early" in line or "sleep" in line and "400" in line:
            print(f"{i}:{line}")
PY
docker exec skykin-freeswitch fs_cli -x reloadxml
echo '==== index ===='
grep -n '20260813k\|mediaStream\|replaceTrack\|enableSenders' \
  /opt/call-center-deployement/call-center/app/agent_dashboard/index.php | head
"""
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
