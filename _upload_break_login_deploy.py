#!/usr/bin/env python3
"""Upload agent dashboard break+login fixes to catbox; print curl deploy for ecs-cc."""
import gzip
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
files = {
    "index.php": root / "app/agent_dashboard/index.php",
    "supervisor.php": root / "app/agent_dashboard/supervisor.php",
}
urls = {}
for name, path in files.items():
    raw = path.read_bytes()
    # markers
    text = raw.decode("utf-8", "replace")
    if name == "index.php":
        assert "skykin_agent_login_at_" in text, "login timer fix missing"
        assert "orphan:" in text or "Orphan FS" in text, "orphan sync missing in index"
    if name == "supervisor.php":
        assert "skykin_cc_status_rank" in text, "break rank fix missing"
    gz = gzip.compress(raw, compresslevel=9)
    print(f"Uploading {name} ({len(raw)} -> {len(gz)} gzip)...")
    r = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"fileToUpload": (name + ".gz", gz, "application/gzip")},
        timeout=120,
    )
    r.raise_for_status()
    url = r.text.strip()
    if not url.startswith("http"):
        raise SystemExit(f"Upload failed for {name}: {url[:200]}")
    urls[name] = url
    print(f"  {url}")

deploy = f'''#!/bin/bash
set -eu
DASH=/opt/skykin/app/app/agent_dashboard
TS=$(date +%Y%m%d-%H%M%S)
cp -a "$DASH/index.php" "$DASH/index.php.bak-$TS"
cp -a "$DASH/supervisor.php" "$DASH/supervisor.php.bak-$TS"
curl -fsSL -o /tmp/index.php.gz '{urls["index.php"]}'
curl -fsSL -o /tmp/supervisor.php.gz '{urls["supervisor.php"]}'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
grep -q skykin_agent_login_at_ /tmp/index.php
grep -q skykin_cc_status_rank /tmp/supervisor.php
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
echo "=== verify ==="
grep -c skykin_agent_login_at_ "$DASH/index.php"
grep -c skykin_cc_status_rank "$DASH/supervisor.php"
grep -c "orphan:" "$DASH/index.php" "$DASH/supervisor.php" || true
echo "DONE — hard-refresh agent + supervisor dashboards"
'''
out = root / "scripts/_deploy_break_login_curl.sh"
out.write_text(deploy.replace("\r\n", "\n"), encoding="utf-8")
print("\nDeploy script:", out)
print("\n--- paste on ecs-cc ---\n")
print(deploy)
