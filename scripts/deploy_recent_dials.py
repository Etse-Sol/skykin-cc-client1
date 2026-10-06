#!/usr/bin/env python3
"""Deploy Recent dials (last 10) UI into live agent index.php."""
import re
import subprocess
import sys

IDX = "/var/www/fusionpbx/app/agent_dashboard/index.php"
src = subprocess.check_output(["docker", "exec", "skykin-web", "cat", IDX], text=True, errors="replace")

if "toggleRecentDials" in src and "dp-recent-list" in src:
    print("Recent dials already present")
    sys.exit(0)

# 1) CSS after .dp-del:hover
css = """
.dp-recent {
    grid-column: 1; background: #f1f5f9; color: #334155; border: 1px solid #e2e8f0;
    border-radius: 20px; min-height: 40px; padding: 8px 12px; font-size: 12px;
    font-weight: 700; cursor: pointer; transition: all .14s ease;
}
.dp-recent:hover, .dp-recent.active { background: #e8f0fe; border-color: #93c5fd; color: #0047AB; }
.dp-recent-list {
    margin-top: 10px; border: 1px solid #e2e8f0; border-radius: 10px;
    background: #fff; max-height: 220px; overflow-y: auto;
}
.dp-recent-item {
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
    width: 100%; padding: 10px 12px; border: none; border-bottom: 1px solid #f1f5f9;
    background: transparent; cursor: pointer; text-align: left; font-size: 13px; color: #0f172a;
}
.dp-recent-item:last-child { border-bottom: none; }
.dp-recent-item:hover { background: #f8fafc; }
.dp-recent-empty { padding: 14px; text-align: center; color: #94a3b8; font-size: 12px; }
"""
if ".dp-row-actions" in src:
    src = src.replace(
        "grid-template-columns: 44px 1fr 44px;",
        "grid-template-columns: auto 1fr 44px;",
        1,
    )
if ".dp-del:hover" in src and "dp-recent-list" not in src:
    src = src.replace(
        ".dp-del:hover { background: #fff1f2; border-color: #fecdd3; color: #e11d48; }",
        ".dp-del:hover { background: #fff1f2; border-color: #fecdd3; color: #e11d48; }\n" + css,
        1,
    )

# 2) HTML buttons
old_actions = """        <div class="dp-row-actions">
            <button class="dp-call" onclick="dpCall()" title="Start call">&#128222;&nbsp; Call</button>
            <button class="dp-del" onclick="dpDelete()" title="Delete last digit" aria-label="Delete last digit">&#9003;</button>
        </div>
    </div>"""
new_actions = """        <div class="dp-row-actions">
            <button class="dp-recent" type="button" onclick="toggleRecentDials()" title="Last 10 numbers you dialed">Recent</button>
            <button class="dp-call" onclick="dpCall()" title="Start call">&#128222;&nbsp; Call</button>
            <button class="dp-del" onclick="dpDelete()" title="Delete last digit" aria-label="Delete last digit">&#9003;</button>
        </div>
        <div id="dpRecentList" class="dp-recent-list" style="display:none" aria-label="Recent dials"></div>
    </div>"""
if old_actions in src:
    src = src.replace(old_actions, new_actions, 1)
    print("HTML Recent button added")
else:
    # looser match
    if "toggleRecentDials" not in src and 'onclick="dpCall()"' in src and "dp-row-actions" in src:
        src = src.replace(
            '<div class="dp-row-actions">\n            <button class="dp-call"',
            '<div class="dp-row-actions">\n            <button class="dp-recent" type="button" onclick="toggleRecentDials()" title="Last 10 numbers you dialed">Recent</button>\n            <button class="dp-call"',
            1,
        )
        if 'id="dpRecentList"' not in src:
            src = src.replace(
                '</div>\n    </div>\n\n    </div>\n</div>\n\n<script src="https://cdn.jsdelivr.net/npm/socket.io',
                '</div>\n        <div id="dpRecentList" class="dp-recent-list" style="display:none" aria-label="Recent dials"></div>\n    </div>\n\n    </div>\n</div>\n\n<script src="https://cdn.jsdelivr.net/npm/socket.io',
                1,
            )
        print("HTML Recent button added (loose)")
    else:
        print("WARN: dial pad actions HTML not matched")

# 3) JS: remember in makeCall + helper functions
js = r'''
// ── Personal recent dials (last 10, this browser / extension) ───────────────
const SKYKIN_RECENT_MAX = 10;
function skykinRecentStorageKey() {
    const ext = localStorage.getItem('sip_ext') || serverExt || 'agent';
    return 'skykin_recent_dials_' + String(ext);
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

if "function rememberRecentDial" not in src:
    # insert before makeCall or after makeCall block
    m = re.search(r"function makeCall\(number\) \{.*?\n\}\n", src, re.S)
    if m:
        block = m.group(0)
        if "rememberRecentDial" not in block:
            block2 = block.replace(
                "lastCallType = 'Outbound';\n    fetchCrmContact(number);",
                "lastCallType = 'Outbound';\n    rememberRecentDial(number);\n    fetchCrmContact(number);",
            )
            if block2 == block:
                block2 = block.replace(
                    "lastCallType = 'Outbound';",
                    "lastCallType = 'Outbound';\n    rememberRecentDial(number);",
                )
            src = src[: m.start()] + block2 + "\n" + js + src[m.end() :]
            print("JS recent dials helpers added")
        else:
            src = src[: m.end()] + "\n" + js + src[m.end() :]
            print("JS helpers added after makeCall")
    else:
        print("ERROR: makeCall not found", file=sys.stderr)
        sys.exit(1)

subprocess.run(
    ["docker", "exec", "-i", "skykin-web", "tee", IDX],
    input=src,
    text=True,
    check=True,
    stdout=subprocess.DEVNULL,
)
print("OK: Recent (last 10) on dial pad. Hard refresh agent page.")
