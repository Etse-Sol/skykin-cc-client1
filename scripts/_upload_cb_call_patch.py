#!/usr/bin/env python3
import base64
import requests

patcher = r'''#!/usr/bin/env python3
import re, subprocess, sys

IDX = "/var/www/fusionpbx/app/agent_dashboard/index.php"
src = subprocess.check_output(["docker", "exec", "skykin-web", "cat", IDX], text=True, errors="replace")

marker_start = "function fetchCallbacks() {"
marker_end = "function completeCallback("

NEW = r"""function fetchCallbacks() {
    const ext = localStorage.getItem('sip_ext') || serverExt || '101';
    fetch('index.php?action=list_callbacks&agent_id=' + encodeURIComponent(ext))
        .then(r => r.json())
        .then(data => {
            const list = data.records || [];
            if (list.length === 0) {
                document.getElementById('callbacksHistoryBody').innerHTML =
                    '<tr><td colspan="6" class="rec-empty">No upcoming callbacks scheduled.</td></tr>';
                return;
            }
            list.sort((a,b) => new Date(a.formatted_time) - new Date(b.formatted_time));
            document.getElementById('callbacksHistoryBody').innerHTML = list.map((c, idx) => {
                const urgentClass = (idx === 0) ? 'class="callback-urgent"' : '';
                const phone = String(c.customer_phone || '').replace(/'/g, '');
                const phoneAttr = encodeURIComponent(phone);
                return `
                    <tr ${urgentClass}>
                        <td>${c.formatted_time}</td>
                        <td>${c.customer_name || 'Unknown'}</td>
                        <td>${c.customer_phone}</td>
                        <td style="max-width:200px; white-space:normal; font-size:12px; color:#555;">${c.notes || '-'}</td>
                        <td><span class="badge" style="background:#ffedd5; color:#ea580c; font-weight:bold;">${c.status}</span></td>
                        <td style="white-space:nowrap">
                            <button type="button" class="btn-filter" style="margin-right:6px" onclick="callFromCallback(decodeURIComponent('${phoneAttr}'))">Call</button>
                            <button class="btn-action-resolve" onclick="completeCallback(${c.callback_id})">Complete</button>
                        </td>
                    </tr>
                `;
            }).join('');
        })
        .catch(() => {
            document.getElementById('callbacksHistoryBody').innerHTML =
                '<tr><td colspan="6" class="rec-empty">Error loading callbacks.</td></tr>';
        });
}

/** Put callback number on dial pad and start outbound (same as dial pad Call). */
function callFromCallback(phone) {
    phone = (phone || '').trim();
    if (!phone) {
        showToast('No phone number on this callback.');
        return;
    }
    try { if (typeof openPhonePopup === 'function') openPhonePopup(); } catch (e) {}
    try { if (typeof switchTab === 'function') switchTab('dashboard'); } catch (e) {}
    makeCall(phone);
}

"""

if "function callFromCallback" in src and "callFromCallback(decodeURIComponent" in src:
    print("Call button already present")
else:
    i = src.find(marker_start)
    j = src.find(marker_end)
    if i < 0 or j < 0 or j <= i:
        print("ERROR: markers not found", file=sys.stderr)
        sys.exit(1)
    src = src[:i] + NEW + src[j:]
    print("Call button JS patched")

old = "WHERE agent_id = :agent AND status = 'Scheduled'"
new = "WHERE status = 'Scheduled'\n                  AND (agent_id = :agent OR agent_id = 'after-hours')"
if old in src:
    src = src.replace(old, new, 1)
    print("list_callbacks after-hours filter patched")

subprocess.run(
    ["docker", "exec", "-i", "skykin-web", "tee", IDX],
    input=src,
    text=True,
    check=True,
    stdout=subprocess.DEVNULL,
)
print("OK deployed. Hard refresh Callbacks tab.")
'''

b64 = base64.b64encode(patcher.encode()).decode()
sh = (
    "#!/bin/bash\n"
    "set -eu\n"
    f"python3 -c \"import base64; open('/tmp/patch_cb_call.py','wb').write(base64.b64decode('{b64}'))\"\n"
    "python3 /tmp/patch_cb_call.py\n"
)
data = sh.encode()
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("patch_cb_call.sh", data, "application/x-sh")},
    timeout=60,
)
print(r.text)
