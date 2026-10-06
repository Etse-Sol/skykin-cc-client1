import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=30):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print(run(r"""
python3 - <<'PY'
from pathlib import Path
p = Path("/opt/call-center-deployement/call-center/app/agent_dashboard/index.php")
# file may only live in the container mount
cands = [
    Path("/opt/call-center-deployement/call-center/app/agent_dashboard/index.php"),
    Path("/tmp/ad_index.php"),
]
text = None
path = None
for c in cands:
    if c.exists():
        text = c.read_text(encoding="utf-8", errors="replace")
        path = c
        break
if text is None:
    raise SystemExit("no file")
text = text.replace(
    "wsUri = wsUri.replace(/^(wss?:\\/\\/)([^/:]+)$/i, '$1$2' + pagePort) + ':7443';",
    "wsUri = wsUri.replace(/^(wss?:\\/\\/)([^/:]+)$/i, '$1$2') + ':7443';",
)
text = text.replace(
    "+ location.hostname + (location.port ? ':' + location.port : '') + ':7443';",
    "+ location.hostname + ':7443';",
)
path.write_text(text, encoding="utf-8")
print("wrote", path)
PY
docker cp /tmp/ad_index.php skykin-web:/var/www/fusionpbx/app/agent_dashboard/index.php 2>/dev/null || true
# if we edited the compose mount, container already has it
ls -l /opt/call-center-deployement/call-center/app/agent_dashboard/index.php 2>/dev/null | head -1
"""))

# If the mount is the compose path, copy that into the container too
print(run("""
if [ -f /opt/call-center-deployement/call-center/app/agent_dashboard/index.php ]; then
  docker cp /opt/call-center-deployement/call-center/app/agent_dashboard/index.php skykin-web:/var/www/fusionpbx/app/agent_dashboard/index.php
fi
docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/index.php
docker exec skykin-web sed -n '5188,5196p' /var/www/fusionpbx/app/agent_dashboard/index.php
"""))

print("==== 7443 listen ====")
print(run("docker exec skykin-freeswitch ss -lnt | grep 7443"))
print(run("timeout 3 curl -skI https://196.189.236.140:7443/ | head -6"))
c.close()
