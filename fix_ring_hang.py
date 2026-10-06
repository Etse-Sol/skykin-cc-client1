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


def run(cmd, timeout=200):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== last 102 ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E 'Processing 102 <|execute_on_answer|playback|Originate Resulted|"
        "has been answered|Bridge Failed|NORMAL_|Hangup sofia/internal/102' "
        "/var/log/freeswitch/freeswitch.log | tail -40\""
    )
)

print("==== strip blocking playback ====")
print(
    run(
        r"""
python3 - <<'PY'
from pathlib import Path
drop = '      <action application="export" data="nolocal:execute_on_answer=playback tone_stream://%(600,0,900)"/>\n'
for p in [
    Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml"),
    Path("/root/skykin-fs-etc/dialplan/01_skykin_client1.skykin.local.xml"),
]:
    t = p.read_text()
    n = t.count("execute_on_answer=playback")
    t = t.replace(drop, "")
    # also drop if whitespace differs
    lines = [ln for ln in t.splitlines(True) if "execute_on_answer=playback" not in ln]
    t2 = "".join(lines)
    p.write_text(t2)
    print(p.name, "removed", n, "tone left", t2.count("tone_stream"))
PY
docker exec skykin-freeswitch fs_cli -x reloadxml
grep -n 'execute_on_answer\|tone_stream\|ignore_early' /root/skykin-fs-etc/dialplan/default/00_skykin.xml | head
"""
    )
)
c.close()
