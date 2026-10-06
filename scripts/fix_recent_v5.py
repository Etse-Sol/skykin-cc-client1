#!/usr/bin/env python3
"""Fix Recent: panel must live inside #dpPanel; remove orphan panels + old JS."""
import re
import subprocess

JS_PATH = "/var/www/fusionpbx/app/agent_dashboard/skykin_recent_dials.js"
PAGES = [
    "/var/www/fusionpbx/app/agent_dashboard/index.php",
    "/var/www/fusionpbx/app/agent_dashboard/supervisor.php",
]

FIXED_JS = r'''/**
 * SkyKin recent dials v5 — panel must be inside #dpPanel (fixes invisible list).
 */
(function () {
  'use strict';
  var MAX = 10;
  var _toggling = false;

  function storageKey() {
    var ext =
      localStorage.getItem('sip_ext') ||
      localStorage.getItem('sup_ext') ||
      localStorage.getItem('sup_sip_ext') ||
      (typeof serverExt !== 'undefined' && serverExt) ||
      (typeof supExt !== 'undefined' && supExt) ||
      'user';
    var prefix = (location.pathname || '').indexOf('supervisor') >= 0 ? 'sup_' : 'agent_';
    return 'skykin_recent_dials_' + prefix + String(ext || 'user');
  }

  function getList() {
    try {
      var raw = JSON.parse(localStorage.getItem(storageKey()) || '[]');
      return Array.isArray(raw) ? raw.filter(Boolean).slice(0, MAX) : [];
    } catch (e) { return []; }
  }

  function saveList(list) {
    localStorage.setItem(storageKey(), JSON.stringify(list.slice(0, MAX)));
  }

  function remember(number) {
    number = String(number || '').trim();
    if (!number || number.length < 3) return;
    var list = getList().filter(function (n) { return n !== number; });
    list.unshift(number);
    saveList(list);
  }

  function ensurePanel() {
    var dp = document.getElementById('dpPanel');
    if (!dp) return null;

    // Prefer panel already inside dial pad
    var panel = dp.querySelector('#dpRecentList') || dp.querySelector('.dp-recent-list');

    // Remove orphan panels elsewhere (wrong place = invisible)
    var all = document.querySelectorAll('#dpRecentList');
    for (var i = 0; i < all.length; i++) {
      if (!dp.contains(all[i])) {
        try { all[i].parentNode.removeChild(all[i]); } catch (e) {}
      }
    }

    if (panel && dp.contains(panel)) {
      panel.id = 'dpRecentList';
      return panel;
    }

    panel = document.createElement('div');
    panel.id = 'dpRecentList';
    panel.className = 'dp-recent-list';
    panel.setAttribute('aria-label', 'Recent dials');
    panel.style.display = 'none';

    var actions = dp.querySelector('.dp-row-actions');
    if (actions && actions.parentNode === dp) {
      if (actions.nextSibling) dp.insertBefore(panel, actions.nextSibling);
      else dp.appendChild(panel);
    } else {
      dp.appendChild(panel);
    }
    return panel;
  }

  function render() {
    var panel = ensurePanel();
    if (!panel) return;
    var list = getList();
    if (!list.length) {
      panel.innerHTML =
        '<div style="padding:14px;text-align:center;color:#94a3b8;font-size:12px;line-height:1.4">' +
        'No recent numbers yet.<br>Dial once, then open Recent.</div>';
      return;
    }
    panel.innerHTML = list.map(function (n) {
      var safe = encodeURIComponent(n);
      var shown = String(n).replace(/</g, '&lt;').replace(/"/g, '&quot;');
      return (
        '<button type="button" class="dp-recent-item" data-num="' + safe + '" ' +
        'style="display:flex;width:100%;box-sizing:border-box;align-items:center;justify-content:space-between;' +
        'gap:8px;padding:10px 12px;border:none;border-bottom:1px solid #f1f5f9;background:#fff;' +
        'cursor:pointer;text-align:left;font-size:13px;color:#0f172a">' +
        '<span>' + shown + '</span>' +
        '<span style="color:#0047AB;font-weight:700;font-size:11px">Call</span></button>'
      );
    }).join('');
  }

  function openPanel() {
    var panel = ensurePanel();
    var btn = document.querySelector('#dpPanel .dp-recent');
    if (!panel) {
      alert('Dial pad not ready — open the phone panel first');
      return;
    }
    var inp = document.getElementById('dialInput');
    var typed = inp ? String(inp.value || '').trim() : '';
    if (typed && getList().length === 0) remember(typed);
    render();
    panel.style.display = 'block';
    panel.style.visibility = 'visible';
    panel.style.maxHeight = '220px';
    panel.style.overflowY = 'auto';
    panel.style.marginTop = '10px';
    panel.style.border = '1px solid #e2e8f0';
    panel.style.borderRadius = '10px';
    panel.style.background = '#fff';
    panel.style.width = '100%';
    panel.style.boxSizing = 'border-box';
    panel.classList.add('open');
    if (btn) btn.classList.add('active');
    var phone = document.getElementById('phonePopup');
    if (phone) {
      setTimeout(function () { phone.scrollTop = phone.scrollHeight; }, 30);
    }
  }

  function closePanel() {
    var dp = document.getElementById('dpPanel');
    var panel = dp ? dp.querySelector('#dpRecentList') : document.getElementById('dpRecentList');
    var btn = document.querySelector('#dpPanel .dp-recent');
    if (panel) {
      panel.style.display = 'none';
      panel.classList.remove('open');
    }
    if (btn) btn.classList.remove('active');
  }

  function toggle() {
    if (_toggling) return;
    _toggling = true;
    try {
      var dp = document.getElementById('dpPanel');
      var panel = dp ? dp.querySelector('#dpRecentList') : null;
      var open = panel && (panel.style.display === 'block' || panel.classList.contains('open'));
      if (open) closePanel();
      else openPanel();
    } finally {
      setTimeout(function () { _toggling = false; }, 100);
    }
  }

  function redial(number) {
    closePanel();
    number = String(number || '').trim();
    if (!number) return;
    if (typeof window.makeCall === 'function') window.makeCall(number);
    else {
      var inp = document.getElementById('dialInput');
      if (inp) inp.value = number;
    }
  }

  window.toggleRecentDials = toggle;
  window.renderRecentDials = render;
  window.rememberRecentDial = remember;
  window.getRecentDials = getList;
  window.redialFromRecent = redial;

  function wrapMakeCall() {
    if (typeof window.makeCall !== 'function' || window.makeCall._skykinRecentWrapped) return;
    var orig = window.makeCall;
    function wrapped(number) {
      var n = number || (document.getElementById('dialInput') && document.getElementById('dialInput').value) || '';
      if (n) remember(n);
      return orig.apply(this, arguments);
    }
    wrapped._skykinRecentWrapped = true;
    window.makeCall = wrapped;
  }

  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.closest) return;
    var recentBtn = t.closest('.dp-recent');
    if (recentBtn) {
      ev.preventDefault();
      ev.stopPropagation();
      if (ev.stopImmediatePropagation) ev.stopImmediatePropagation();
      toggle();
      return;
    }
    var item = t.closest('.dp-recent-item');
    if (item) {
      ev.preventDefault();
      if (ev.stopImmediatePropagation) ev.stopImmediatePropagation();
      var num = item.getAttribute('data-num') || '';
      try { num = decodeURIComponent(num); } catch (e) {}
      redial(num);
    }
  }, true);

  function boot() {
    wrapMakeCall();
    setTimeout(wrapMakeCall, 500);
    setTimeout(wrapMakeCall, 2000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
'''


def tee(path, text):
    p = subprocess.Popen(
        ["docker", "exec", "-i", "skykin-web", "tee", path],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
    )
    p.communicate(text.encode())
    if p.returncode:
        raise SystemExit("tee failed " + path)


print("1) Write JS v5")
tee(JS_PATH, FIXED_JS)

print("2) Fix HTML + strip old inline recent JS + load script LAST")
for page in PAGES:
    src = subprocess.check_output(["docker", "exec", "skykin-web", "cat", page], text=True, errors="replace")

    # Remove ALL dpRecentList nodes
    src = re.sub(
        r'\s*<div id="dpRecentList"[^>]*>\s*</div>\s*',
        '\n',
        src,
    )

    # Insert one correctly after first dp-row-actions block that has dp-recent
    m = re.search(
        r'(<div class="dp-row-actions">[\s\S]*?class="dp-recent"[\s\S]*?</div>)',
        src,
    )
    if m:
        insert_at = m.end()
        src = (
            src[:insert_at]
            + '\n        <div id="dpRecentList" class="dp-recent-list" style="display:none" aria-label="Recent dials"></div>'
            + src[insert_at:]
        )
        print("   ", page, ": dpRecentList placed under dial pad")
    else:
        print("   ", page, ": WARN no dp-row-actions+dp-recent found")

    # Remove onclick on Recent
    src = src.replace('onclick="toggleRecentDials()"', "")
    src = src.replace("onclick='toggleRecentDials()'", "")

    # Neutralize old inline recent functions so they cannot override v5
    # Rename declarations to dead names
    for fn in (
        "skykinRecentStorageKey",
        "getRecentDials",
        "rememberRecentDial",
        "renderRecentDials",
        "toggleRecentDials",
        "redialFromRecent",
    ):
        src = re.sub(
            rf"\bfunction {fn}\b",
            f"function __dead_{fn}",
            src,
        )
        src = re.sub(
            rf"\bconst SKYKIN_RECENT_MAX\b",
            "const __DEAD_SKYKIN_RECENT_MAX",
            src,
            count=1,
        )

    # Ensure makeCall still safe if it calls rememberRecentDial
    # (v5 wraps makeCall anyway)

    # Script tag: remove old ones, append before </body> as LAST script
    src = re.sub(
        r'\s*<script src="/app/agent_dashboard/skykin_recent_dials\.js[^"]*"></script>\s*',
        "\n",
        src,
    )
    src = re.sub(
        r'\s*<script src="skykin_recent_dials\.js[^"]*"></script>\s*',
        "\n",
        src,
    )
    if "</body>" in src:
        src = src.replace(
            "</body>",
            '    <script src="/app/agent_dashboard/skykin_recent_dials.js?v=5"></script>\n</body>',
            1,
        )
    else:
        src += '\n<script src="/app/agent_dashboard/skykin_recent_dials.js?v=5"></script>\n'

    tee(page, src)
    print("   ", page, ": patched")

print("3) Verify panel next to Recent button")
print(
    subprocess.check_output(
        "docker exec skykin-web sh -c '"
        "grep -n \"dp-recent\\|dpRecentList\\|skykin_recent_dials.js\" "
        "/var/www/fusionpbx/app/agent_dashboard/index.php | head -25; echo ---; "
        "grep -n \"dp-recent\\|dpRecentList\\|skykin_recent_dials.js\" "
        "/var/www/fusionpbx/app/agent_dashboard/supervisor.php | head -25'",
        shell=True,
        text=True,
        errors="replace",
    )
)
print("OK. Hard refresh BOTH pages (Ctrl+Shift+R). Open phone, tap Recent.")
print("Expect list directly under Recent/phone/delete buttons.")
