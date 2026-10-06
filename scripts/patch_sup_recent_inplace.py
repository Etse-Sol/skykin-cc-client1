#!/usr/bin/env python3
"""Small in-place patch: add Recent dials to live supervisor.php (no huge argv)."""
import subprocess
import sys

IDX = "/var/www/fusionpbx/app/agent_dashboard/supervisor.php"
src = subprocess.check_output(["docker", "exec", "skykin-web", "cat", IDX], text=True, errors="replace")

if "toggleRecentDials" in src and "dpRecentList" in src and "&#128338; Recent" in src:
    print("OK: Recent already present (new placement)")
    sys.exit(0)

# If older Recent beside Call exists, upgrade placement
if "toggleRecentDials" in src and "dp-recent" in src:
    print("Older Recent found — upgrading to title-row button")

CSS = """
.dp-recent{background:#f1f5f9;color:#334155;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
.dp-recent:hover,.dp-recent.active{background:#e8f0fe;border-color:#93c5fd;color:#0047AB}
.dp-recent-list{margin-top:10px;border:1px solid #e2e8f0;border-radius:10px;background:#fff;max-height:220px;overflow-y:auto}
.dp-recent-item{display:flex;align-items:center;justify-content:space-between;gap:8px;width:100%;padding:10px 12px;border:none;border-bottom:1px solid #f1f5f9;background:transparent;cursor:pointer;text-align:left;font-size:13px;color:#0f172a}
.dp-recent-item:last-child{border-bottom:none}
.dp-recent-item:hover{background:#f8fafc}
.dp-recent-empty{padding:14px;text-align:center;color:#94a3b8;font-size:12px}
"""

JS = r'''
// Personal recent dials (last 10) — supervisor softphone
const SKYKIN_RECENT_MAX = 10;
function skykinRecentStorageKey() {
    const ext = localStorage.getItem('sup_ext') || localStorage.getItem('sup_sip_ext') || serverExt || 'supervisor';
    return 'skykin_recent_dials_sup_' + String(ext);
}
function getRecentDials() {
    try {
        const raw = JSON.parse(localStorage.getItem(skykinRecentStorageKey()) || '[]');
        return Array.isArray(raw) ? raw.filter(Boolean).slice(0, SKYKIN_RECENT_MAX) : [];
    } catch (e) { return []; }
}
function rememberRecentDial(number) {
    number = String(number || '').trim();
    if (!number || number.length < 3) return;
    const list = getRecentDials().filter(n => n !== number);
    list.unshift(number);
    localStorage.setItem(skykinRecentStorageKey(), JSON.stringify(list.slice(0, SKYKIN_RECENT_MAX)));
    const panel = document.getElementById('dpRecentList');
    if (panel && panel.style.display === 'block') renderRecentDials();
}
function renderRecentDials() {
    const panel = document.getElementById('dpRecentList');
    if (!panel) return;
    const list = getRecentDials();
    if (!list.length) {
        panel.innerHTML = '<div class="dp-recent-empty">No recent numbers yet. Dial someone first.</div>';
        return;
    }
    panel.innerHTML = list.map(n => {
        const safe = encodeURIComponent(n);
        return '<button type="button" class="dp-recent-item" onclick="redialFromRecent(decodeURIComponent(\'' + safe + '\'))">'
            + '<span>' + String(n).replace(/</g,'&lt;') + '</span><span style="color:#0047AB;font-weight:700;font-size:11px">Call</span>'
            + '</button>';
    }).join('');
}
function toggleRecentDials() {
    const panel = document.getElementById('dpRecentList');
    const btn = document.querySelector('.dp-recent');
    if (!panel) return;
    const isOpen = panel.style.display === 'block';
    if (isOpen) {
        panel.style.display = 'none';
        if (btn) btn.classList.remove('active');
    } else {
        renderRecentDials();
        panel.style.display = 'block';
        if (btn) btn.classList.add('active');
    }
}
function redialFromRecent(number) {
    const panel = document.getElementById('dpRecentList');
    const btn = document.querySelector('.dp-recent');
    if (panel) panel.style.display = 'none';
    if (btn) btn.classList.remove('active');
    makeCall(number);
}
'''

changed = False

# CSS
if "dp-recent-list" not in src:
    if ".dp-call{" in src:
        src = src.replace(".dp-call{", CSS + "\n.dp-call{", 1)
        changed = True
        print("CSS added")
    else:
        print("WARN: .dp-call CSS not found")

# HTML — title row button (preferred)
old_title = '<div class="dp-title">Dial number</div>\n        <input type="tel" class="dp-display" id="dialInput"'
new_title = (
    '<div class="dp-title" style="display:flex;align-items:center;justify-content:space-between;gap:8px">\n'
    '            <span>Dial number</span>\n'
    '            <button class="dp-recent" type="button" onclick="toggleRecentDials()" title="Last 10 numbers you dialed" style="min-height:32px;padding:6px 12px">&#128338; Recent</button>\n'
    '        </div>\n'
    '        <input type="tel" class="dp-display" id="dialInput"'
)
if '&#128338; Recent' not in src:
    if old_title in src:
        src = src.replace(old_title, new_title, 1)
        changed = True
        print("Title Recent button added")
    elif 'onclick="toggleRecentDials()"' not in src:
        # try insert before dp-call row
        needle = '<div class="dp-row-actions">\n            <button class="dp-call"'
        insert = (
            '<div class="dp-title" style="display:flex;justify-content:flex-end;margin-bottom:8px">'
            '<button class="dp-recent" type="button" onclick="toggleRecentDials()">&#128338; Recent</button></div>\n'
            '        <div class="dp-row-actions">\n            <button class="dp-call"'
        )
        if needle in src:
            src = src.replace(needle, insert, 1)
            changed = True
            print("Recent button inserted above Call row")
        else:
            print("ERROR: dial pad HTML not found", file=sys.stderr)
            sys.exit(1)

# Remove duplicate Recent in dp-row-actions if both exist
src2 = src.replace(
    '<button class="dp-recent" type="button" onclick="toggleRecentDials()" title="Last 10 numbers you dialed">Recent</button>\n            <button class="dp-call"',
    '<button class="dp-call"',
)
if src2 != src:
    src = src2
    changed = True
    print("Removed duplicate Recent beside Call")

# recent list panel after dial input
if 'id="dpRecentList"' not in src:
    needle = 'id="dialInput" placeholder="Enter number..." maxlength="20" autocomplete="off" inputmode="tel">\n        <div class="dp-grid">'
    insert = (
        'id="dialInput" placeholder="Enter number..." maxlength="20" autocomplete="off" inputmode="tel">\n'
        '        <div id="dpRecentList" class="dp-recent-list" style="display:none" aria-label="Recent dials"></div>\n'
        '        <div class="dp-grid">'
    )
    if needle in src:
        src = src.replace(needle, insert, 1)
        changed = True
        print("Recent list panel added")
    else:
        # alternate placeholder
        needle2 = 'id="dialInput"'
        # find first dialInput and insert after its closing tag line
        idx = src.find('id="dialInput"')
        if idx > 0:
            end = src.find(">", idx)
            # find end of tag line
            nl = src.find("\n", end)
            if nl > 0 and 'dpRecentList' not in src[end:end+200]:
                src = src[: nl + 1] + '        <div id="dpRecentList" class="dp-recent-list" style="display:none" aria-label="Recent dials"></div>\n' + src[nl + 1 :]
                changed = True
                print("Recent list panel added (alt)")

# JS helpers
if "function toggleRecentDials" not in src:
    marker = "function makeCall(number) {"
    i = src.find(marker)
    if i < 0:
        print("ERROR: makeCall not found", file=sys.stderr)
        sys.exit(1)
    # find end of makeCall function (first }\n after start at brace depth)
    j = i + len(marker)
    depth = 0
    started = False
    k = i
    while k < len(src):
        ch = src[k]
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                k += 1
                break
        k += 1
    make_block = src[i:k]
    if "rememberRecentDial" not in make_block:
        make_block2 = make_block.replace(
            "lastDialedNumber = number;",
            "lastDialedNumber = number;\n    rememberRecentDial(number);",
            1,
        )
        src = src[:i] + make_block2 + "\n" + JS + src[k:]
    else:
        src = src[:k] + "\n" + JS + src[k:]
    changed = True
    print("JS helpers added")
elif "rememberRecentDial(number)" not in src:
    src = src.replace(
        "lastDialedNumber = number;",
        "lastDialedNumber = number;\n    rememberRecentDial(number);",
        1,
    )
    changed = True
    print("rememberRecentDial hooked into makeCall")

if not changed and "toggleRecentDials" in src:
    print("OK: already patched")
else:
    subprocess.run(
        ["docker", "exec", "-i", "skykin-web", "tee", IDX],
        input=src,
        text=True,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    print("OK: supervisor Recent dials patched")

print("Verify:")
subprocess.run(
    ["docker", "exec", "skykin-web", "grep", "-n", "toggleRecentDials\\|dpRecentList\\|Recent", IDX],
    check=False,
)
print("Hard refresh Supervisor (Ctrl+Shift+R), open blue phone — Recent at top of dial pad.")
