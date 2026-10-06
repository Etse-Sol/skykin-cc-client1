/**
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
