#!/usr/bin/env python3
"""Deploy skykin_recent_dials.js + script tags for agent + supervisor."""
import base64
import subprocess
import sys

# Embedded JS (kept in this installer so one curl works)
JS = r'''
/**
 * SkyKin recent dials (last 10) — agent + supervisor softphone.
 */
(function () {
  'use strict';
  var MAX = 10;

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
    if (panel && (panel.style.display === 'block' || panel.classList.contains('open'))) {
      render();
    }
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
    if (actions && actions.parentNode) {
      actions.parentNode.insertBefore(panel, actions.nextSibling);
    } else {
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
    panel.innerHTML = list
      .map(function (n) {
        var safe = encodeURIComponent(n);
        var shown = String(n).replace(/</g, '&lt;').replace(/"/g, '&quot;');
        return (
          '<button type="button" class="dp-recent-item" data-num="' +
          safe +
          '" style="display:flex;width:100%;align-items:center;justify-content:space-between;gap:8px;padding:10px 12px;border:none;border-bottom:1px solid #f1f5f9;background:transparent;cursor:pointer;text-align:left;font-size:13px;color:#0f172a">' +
          '<span>' +
          shown +
          '</span><span style="color:#0047AB;font-weight:700;font-size:11px">Call</span></button>'
        );
      })
      .join('');
  }

  function openPanel() {
    var panel = ensurePanel();
    var btn = document.querySelector('#dpPanel .dp-recent') || document.querySelector('.dp-recent');
    if (!panel) {
      alert('Recent list unavailable — hard refresh (Ctrl+Shift+R)');
      return;
    }
    var typed = '';
    var inp = document.getElementById('dialInput');
    if (inp) typed = String(inp.value || '').trim();
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
    var panel = document.getElementById('dpRecentList');
    var open = panel && (panel.style.display === 'block' || panel.classList.contains('open'));
    if (open) closePanel();
    else openPanel();
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

  document.addEventListener(
    'click',
    function (ev) {
      var t = ev.target;
      if (!t || !t.closest) return;
      var recentBtn = t.closest('.dp-recent');
      if (recentBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        toggle();
        return;
      }
      var item = t.closest('.dp-recent-item');
      if (item) {
        ev.preventDefault();
        var num = item.getAttribute('data-num') || '';
        try { num = decodeURIComponent(num); } catch (e) {}
        redial(num);
      }
    },
    true
  );

  function boot() {
    wrapMakeCall();
    setTimeout(wrapMakeCall, 500);
    setTimeout(wrapMakeCall, 2000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
'''.lstrip()

TAG = '<script src="/app/agent_dashboard/skykin_recent_dials.js?v=3"></script>'

def sh(cmd):
    return subprocess.check_output(cmd, shell=True, text=True, errors="replace")

def docker_write(path, data: bytes):
    p = subprocess.Popen(
        ["docker", "exec", "-i", "skykin-web", "tee", path],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
    )
    p.communicate(data)
    if p.returncode:
        raise SystemExit("tee failed " + path)

def ensure_script(php_path):
    src = subprocess.check_output(["docker", "exec", "skykin-web", "cat", php_path], text=True, errors="replace")
    if "skykin_recent_dials.js" in src:
        print(php_path, ": script tag already present")
        # bump version
        if "skykin_recent_dials.js?v=3" not in src:
            src = src.replace("skykin_recent_dials.js?v=2", "skykin_recent_dials.js?v=3")
            src = src.replace("skykin_recent_dials.js\"", "skykin_recent_dials.js?v=3\"")
            docker_write(php_path, src.encode())
            print("  bumped cache version")
        return
    # insert before </body> or after idle_watch
    if "</body>" in src:
        src = src.replace("</body>", "    " + TAG + "\n</body>", 1)
    elif "idle_watch.js" in src:
        src = src.replace(
            '<script src="idle_watch.js?v=20260818"></script>',
            '<script src="idle_watch.js?v=20260818"></script>\n' + TAG,
            1,
        )
    else:
        src += "\n" + TAG + "\n"
    # ensure Recent button class exists
    if 'class="dp-recent"' not in src and "dp-row-actions" in src:
        src = src.replace(
            '<div class="dp-row-actions">\n            <button class="dp-call"',
            '<div class="dp-row-actions">\n            <button class="dp-recent" type="button" title="Last 10 numbers">Recent</button>\n            <button class="dp-call"',
            1,
        )
        print("  added Recent button")
    docker_write(php_path, src.encode())
    print(php_path, ": script tag added")

print("Writing JS file...")
docker_write("/var/www/fusionpbx/app/agent_dashboard/skykin_recent_dials.js", JS.encode())
print("Patching pages...")
ensure_script("/var/www/fusionpbx/app/agent_dashboard/index.php")
ensure_script("/var/www/fusionpbx/app/agent_dashboard/supervisor.php")
print("Verify:")
print(sh("docker exec skykin-web ls -la /var/www/fusionpbx/app/agent_dashboard/skykin_recent_dials.js"))
print(sh("docker exec skykin-web grep -n skykin_recent_dials /var/www/fusionpbx/app/agent_dashboard/index.php /var/www/fusionpbx/app/agent_dashboard/supervisor.php"))
print("OK. Hard refresh BOTH pages (Ctrl+Shift+R). Open phone → Recent.")
