#!/bin/bash
# Fix: inbound ring shows Answer/Decline (not Customer Lookup tab). Run on ecs-cc as root.
set -eu
APP=/opt/skykin/app/app/agent_dashboard/index.php
test -f "$APP" || APP=/opt/call-center-deployement/call-center/app/agent_dashboard/index.php
test -f "$APP" || { echo "index.php not found"; exit 1; }

cp -a "$APP" "${APP}.bak-ring-$(date +%Y%m%d%H%M)"

python3 - <<'PY'
from pathlib import Path
import re
p = Path("/opt/skykin/app/app/agent_dashboard/index.php")
if not p.exists():
    p = Path("/opt/call-center-deployement/call-center/app/agent_dashboard/index.php")
text = p.read_text(encoding="utf-8", errors="replace")

old = """    if (callerNumber) {
        fetchCrmContact(callerNumber);
        if (window.performLookup) {
            performLookup(callerNumber);
            switchTab('lookup');
        }
    }"""

new = """    if (callerNumber) {
        // CRM name on phone popup only — lookup tab opens on answer (startCallUI).
        fetchCrmContact(callerNumber);
    }"""

if old not in text:
    if "lookup tab opens on answer" in text:
        print("already patched")
    else:
        raise SystemExit("handleIncoming block not found — patch manually")
else:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("patched handleIncoming")

if "openPhonePopup();" not in text.split("state === 'ringing'")[1].split("} else if")[0]:
    text = p.read_text(encoding="utf-8", errors="replace")
    text = text.replace(
        "} else if (state === 'ringing') {\n"
        "        dot.classList.add('ringing'); badge.classList.add('show'); fab.classList.add('ringing');\n"
        "        document.getElementById('callTimer').style.display = 'none';",
        "} else if (state === 'ringing') {\n"
        "        dot.classList.add('ringing'); badge.classList.add('show'); fab.classList.add('ringing');\n"
        "        openPhonePopup();\n"
        "        document.getElementById('callTimer').style.display = 'none';",
        1,
    )
    p.write_text(text, encoding="utf-8")
    print("patched setSipStatus ringing")
PY

docker cp "$APP" skykin-web:/var/www/fusionpbx/app/agent_dashboard/index.php
docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/index.php
docker exec skykin-web grep -A4 "function handleIncoming" /var/www/fusionpbx/app/agent_dashboard/index.php | head -20
echo "DONE — agents: Ctrl+Shift+R on dashboard, then test inbound"
