#!/usr/bin/env python3
"""Fix supervisor Recent click — ensure list panel + robust toggle."""
import re
import subprocess

IDX = "/var/www/fusionpbx/app/agent_dashboard/supervisor.php"
src = subprocess.check_output(["docker", "exec", "skykin-web", "cat", IDX], text=True, errors="replace")

NEW_FUNCS = r'''
function renderRecentDials() {
    let panel = document.getElementById('dpRecentList');
    if (!panel) {
        const actions = document.querySelector('.dp-row-actions');
        panel = document.createElement('div');
        panel.id = 'dpRecentList';
        panel.className = 'dp-recent-list';
        panel.setAttribute('aria-label', 'Recent dials');
        if (actions && actions.parentNode) actions.parentNode.insertBefore(panel, actions.nextSibling);
        else {
            const dp = document.getElementById('dpPanel');
            if (dp) dp.appendChild(panel);
        }
    }
    const list = getRecentDials();
    if (!list.length) {
        panel.innerHTML = '<div class="dp-recent-empty">No recent numbers yet.<br>Dial a number first, then open Recent.</div>';
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
    let panel = document.getElementById('dpRecentList');
    const btn = document.querySelector('#dpPanel .dp-recent') || document.querySelector('.dp-recent');
    if (!panel) {
        renderRecentDials();
        panel = document.getElementById('dpRecentList');
    }
    if (!panel) {
        if (typeof toast === 'function') toast('Recent list unavailable — hard refresh the page', '#c62828');
        else alert('Recent list unavailable — hard refresh (Ctrl+Shift+R)');
        return;
    }
    const isOpen = panel.style.display === 'block' || panel.classList.contains('open');
    if (isOpen) {
        panel.style.display = 'none';
        panel.classList.remove('open');
        if (btn) btn.classList.remove('active');
    } else {
        const typed = (document.getElementById('dialInput') && document.getElementById('dialInput').value || '').trim();
        if (typed && getRecentDials().length === 0) rememberRecentDial(typed);
        renderRecentDials();
        panel.style.display = 'block';
        panel.classList.add('open');
        if (btn) btn.classList.add('active');
        try { panel.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch (e) {}
        const phone = document.getElementById('phonePopup');
        if (phone) phone.scrollTop = phone.scrollHeight;
    }
}
function redialFromRecent(number) {
    const panel = document.getElementById('dpRecentList');
    const btn = document.querySelector('#dpPanel .dp-recent') || document.querySelector('.dp-recent');
    if (panel) { panel.style.display = 'none'; panel.classList.remove('open'); }
    if (btn) btn.classList.remove('active');
    makeCall(number);
}
'''

# Replace from function renderRecentDials through end of redialFromRecent
pat = re.compile(
    r"function renderRecentDials\(\)\s*\{.*?function redialFromRecent\(number\)\s*\{.*?\n\}",
    re.S,
)
if pat.search(src):
    src = pat.sub(NEW_FUNCS.strip(), src, count=1)
    print("Replaced render/toggle/redial functions")
elif "function toggleRecentDials" in src:
    # replace only toggle + render separately
    src = re.sub(
        r"function toggleRecentDials\(\)\s*\{.*?\n\}",
        NEW_FUNCS.strip().split("function toggleRecentDials")[0]
        + "function toggleRecentDials"
        + NEW_FUNCS.strip().split("function toggleRecentDials")[1].split("function redialFromRecent")[0]
        + "function redialFromRecent"
        + NEW_FUNCS.strip().split("function redialFromRecent")[1],
        src,
        count=1,
        flags=re.S,
    )
    print("Patched toggle (alt)")
else:
    # inject before dpCall or after makeCall block
    if "function makeCall(number)" in src:
        # append helpers after rememberRecentDial section if partial
        marker = "// Personal recent dials"
        if marker in src:
            # wipe broken section from marker to next function that's not recent
            i = src.find(marker)
            j = src.find("\nfunction startRingtone", i)
            if j < 0:
                j = src.find("\nfunction startCallUI", i)
            if j > i:
                helpers = """
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
    if (panel && (panel.style.display === 'block' || panel.classList.contains('open'))) renderRecentDials();
}
""" + NEW_FUNCS
                src = src[:i] + helpers + src[j:]
                print("Rebuilt recent dials section")
            else:
                print("ERROR: could not find section end")
                raise SystemExit(1)
        else:
            # insert after makeCall closing — find rememberRecentDial call already in makeCall
            src = src.replace(
                "else toast('SIP not ready - open phone settings', '#c62828');\n}",
                "else toast('SIP not ready - open phone settings', '#c62828');\n}\n\n"
                "// Personal recent dials (last 10)\n"
                "const SKYKIN_RECENT_MAX = 10;\n"
                "function skykinRecentStorageKey() {\n"
                "    const ext = localStorage.getItem('sup_ext') || localStorage.getItem('sup_sip_ext') || serverExt || 'supervisor';\n"
                "    return 'skykin_recent_dials_sup_' + String(ext);\n"
                "}\n"
                "function getRecentDials() {\n"
                "    try {\n"
                "        const raw = JSON.parse(localStorage.getItem(skykinRecentStorageKey()) || '[]');\n"
                "        return Array.isArray(raw) ? raw.filter(Boolean).slice(0, SKYKIN_RECENT_MAX) : [];\n"
                "    } catch (e) { return []; }\n"
                "}\n"
                "function rememberRecentDial(number) {\n"
                "    number = String(number || '').trim();\n"
                "    if (!number || number.length < 3) return;\n"
                "    const list = getRecentDials().filter(n => n !== number);\n"
                "    list.unshift(number);\n"
                "    localStorage.setItem(skykinRecentStorageKey(), JSON.stringify(list.slice(0, SKYKIN_RECENT_MAX)));\n"
                "}\n"
                + NEW_FUNCS + "\n",
                1,
            )
            if "rememberRecentDial(number)" not in src.split("function makeCall")[1][:800]:
                src = src.replace(
                    "lastDialedNumber = number;",
                    "lastDialedNumber = number;\n    if (typeof rememberRecentDial === 'function') rememberRecentDial(number);",
                    1,
                )
            print("Injected recent dials helpers")
    else:
        print("ERROR: makeCall missing")
        raise SystemExit(1)

# Ensure HTML panel below buttons
if 'id="dpRecentList"' not in src:
    src = src.replace(
        '</div>\n    </div>\n</div>\n<audio id="remoteAudio"',
        '</div>\n        <div id="dpRecentList" class="dp-recent-list" style="display:none" aria-label="Recent dials"></div>\n    </div>\n</div>\n<audio id="remoteAudio"',
        1,
    )
    print("Added dpRecentList HTML")
else:
    # move below row-actions if currently above grid
    if re.search(r'id="dpRecentList".*?dp-grid', src, re.S):
        src = re.sub(r'\s*<div id="dpRecentList"[^>]*>\s*</div>\s*', '\n', src, count=1)
        src = src.replace(
            '            <button class="dp-del" onclick="dpDelete()" aria-label="Delete">&#9003;</button>\n        </div>',
            '            <button class="dp-del" onclick="dpDelete()" aria-label="Delete">&#9003;</button>\n        </div>\n'
            '        <div id="dpRecentList" class="dp-recent-list" style="display:none" aria-label="Recent dials"></div>',
            1,
        )
        print("Moved dpRecentList below buttons")

# CSS open class
if ".dp-recent-list.open" not in src:
    src = src.replace(
        ".dp-recent-list{",
        ".dp-recent-list.open{display:block !important}\n.dp-recent-list{",
        1,
    )
    print("CSS .open added")

# onclick must call toggleRecentDials
if 'onclick="toggleRecentDials()"' not in src:
    src = src.replace(
        'class="dp-recent"',
        'class="dp-recent" type="button" onclick="toggleRecentDials()"',
        1,
    )
    print("Wired Recent onclick")

subprocess.run(
    ["docker", "exec", "-i", "skykin-web", "tee", IDX],
    input=src,
    text=True,
    check=True,
    stdout=subprocess.DEVNULL,
)
print("OK")
subprocess.run(
    ["docker", "exec", "skykin-web", "grep", "-n", "toggleRecentDials\\|dpRecentList\\|scrollIntoView", IDX],
    check=False,
)
print("Hard refresh Supervisor (Ctrl+Shift+R). Click Recent — list should open below buttons.")
print("First time: type a number or dial once, then Recent.")
