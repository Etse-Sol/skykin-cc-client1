#!/usr/bin/env python3
"""Fix Recent double-toggle: open then immediately close on same click."""
import re
import subprocess

JS_PATH = "/var/www/fusionpbx/app/agent_dashboard/skykin_recent_dials.js"
PAGES = [
    "/var/www/fusionpbx/app/agent_dashboard/index.php",
    "/var/www/fusionpbx/app/agent_dashboard/supervisor.php",
]

FIXED_JS = r'''/**
 * SkyKin recent dials (last 10) — agent + supervisor.
 * v4: stopImmediatePropagation + toggle guard (fixes open-then-close).
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
    } catch (e) {
      return [];
    }
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
    var panel = document.getElementById('dpRecentList');
    if (panel && (panel.style.display === 'block' || panel.classList.contains('open'))) render();
  }

  function ensurePanel() {
    var panel = document.getElementById('dpRecentList');
    if (panel) return panel;
    panel = document.createElement('div');
    panel.id = 'dpRecentList';
    panel.className = 'dp-recent-list';
    panel.setAttribute('aria-label', 'Recent dials');
    panel.style.display = 'none';
    var actions = document.querySelector('#dpPanel .dp-row-actions') || document.querySelector('.dp-row-actions');
    if (actions && actions.parentNode) actions.parentNode.insertBefore(panel, actions.nextSibling);
    else {
      var dp = document.getElementById('dpPanel');
      if (dp) dp.appendChild(panel);
    }
    return panel;
  }

  function render() {
    var panel = ensurePanel();
    if (!panel) return;
    var list = getList();
    if (!list.length) {
      panel.innerHTML =
        '<div class="dp-recent-empty" style="padding:14px;text-align:center;color:#94a3b8;font-size:12px">' +
        'No recent numbers yet.<br>Dial once, then open Recent.</div>';
      return;
    }
    panel.innerHTML = list.map(function (n) {
      var safe = encodeURIComponent(n);
      var shown = String(n).replace(/</g, '&lt;').replace(/"/g, '&quot;');
      return (
        '<button type="button" class="dp-recent-item" data-num="' + safe + '" ' +
        'style="display:flex;width:100%;align-items:center;justify-content:space-between;gap:8px;' +
        'padding:10px 12px;border:none;border-bottom:1px solid #f1f5f9;background:transparent;' +
        'cursor:pointer;text-align:left;font-size:13px;color:#0f172a">' +
        '<span>' + shown + '</span>' +
        '<span style="color:#0047AB;font-weight:700;font-size:11px">Call</span></button>'
      );
    }).join('');
  }

  function openPanel() {
    var panel = ensurePanel();
    var btn = document.querySelector('#dpPanel .dp-recent') || document.querySelector('.dp-recent');
    if (!panel) {
      alert('Recent list unavailable — hard refresh (Ctrl+Shift+R)');
      return;
    }
    var inp = document.getElementById('dialInput');
    var typed = inp ? String(inp.value || '').trim() : '';
    if (typed && getList().length === 0) remember(typed);
    render();
    panel.style.cssText =
      'display:block;visibility:visible;max-height:220px;overflow-y:auto;' +
      'margin-top:10px;border:1px solid #e2e8f0;border-radius:10px;background:#fff;';
    panel.classList.add('open');
    if (btn) btn.classList.add('active');
    try { panel.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch (e) {}
    var phone = document.getElementById('phonePopup');
    if (phone) phone.scrollTop = phone.scrollHeight;
  }

  function closePanel() {
    var panel = document.getElementById('dpRecentList');
    var btn = document.querySelector('#dpPanel .dp-recent') || document.querySelector('.dp-recent');
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
      var panel = document.getElementById('dpRecentList');
      var open = panel && (panel.style.display === 'block' || panel.classList.contains('open'));
      if (open) closePanel();
      else openPanel();
    } finally {
      setTimeout(function () { _toggling = false; }, 80);
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


def tee(path, data: str):
    p = subprocess.Popen(
        ["docker", "exec", "-i", "skykin-web", "tee", path],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
    )
    p.communicate(data.encode())
    if p.returncode:
        raise SystemExit("tee failed: " + path)


print("1) Write skykin_recent_dials.js v4")
tee(JS_PATH, FIXED_JS)

print("2) Strip inline onclick + force ?v=4 on both pages")
for page in PAGES:
    src = subprocess.check_output(["docker", "exec", "skykin-web", "cat", page], text=True, errors="replace")
    src2 = src.replace('onclick="toggleRecentDials()"', "")
    src2 = src2.replace("onclick='toggleRecentDials()'", "")
    src2 = re.sub(
        r'<button\s+class="dp-recent"[^>]*>',
        '<button class="dp-recent" type="button" title="Last 10 numbers you dialed">',
        src2,
        count=5,
    )
    if "skykin_recent_dials.js" in src2:
        src2 = re.sub(r"skykin_recent_dials\.js(\?v=\d+)?", "skykin_recent_dials.js?v=4", src2)
    else:
        src2 = src2.replace(
            "</body>",
            '    <script src="/app/agent_dashboard/skykin_recent_dials.js?v=4"></script>\n</body>',
            1,
        )
    tee(page, src2)
    print("   ", page)

print("3) Verify")
out = subprocess.check_output(
    "docker exec skykin-web sh -c '"
    "grep -n \"stopImmediatePropagation\\|skykin_recent_dials.js\" "
    "/var/www/fusionpbx/app/agent_dashboard/skykin_recent_dials.js | head -5; "
    "grep -n \"skykin_recent_dials.js\\|dp-recent\" "
    "/var/www/fusionpbx/app/agent_dashboard/index.php "
    "/var/www/fusionpbx/app/agent_dashboard/supervisor.php | head -20'",
    shell=True,
    text=True,
    errors="replace",
)
print(out)
print("OK — Ctrl+Shift+R on Agent and Supervisor, tap Recent once.")
print("You should see the list OR 'No recent numbers yet' under the buttons.")
