#!/usr/bin/env python3
"""Move supervisor Recent button to bottom (match agent): beside Call."""
import subprocess
import sys

IDX = "/var/www/fusionpbx/app/agent_dashboard/supervisor.php"
src = subprocess.check_output(["docker", "exec", "skykin-web", "cat", IDX], text=True, errors="replace")

# Remove title-row Recent if present
old_title_block = (
    '<div class="dp-title" style="display:flex;align-items:center;justify-content:space-between;gap:8px">\n'
    '            <span>Dial number</span>\n'
    '            <button class="dp-recent" type="button" onclick="toggleRecentDials()" title="Last 10 numbers you dialed" style="min-height:32px;padding:6px 12px">&#128338; Recent</button>\n'
    '        </div>'
)
if old_title_block in src:
    src = src.replace(old_title_block, '<div class="dp-title">Dial number</div>', 1)
    print("Removed top Recent")
else:
    # looser: any title with Recent button
    import re
    src2, n = re.subn(
        r'<div class="dp-title"[^>]*>\s*<span>Dial number</span>\s*<button class="dp-recent"[^>]*>.*?</button>\s*</div>',
        '<div class="dp-title">Dial number</div>',
        src,
        count=1,
        flags=re.S,
    )
    if n:
        src = src2
        print("Removed top Recent (regex)")

# Ensure Recent is in dp-row-actions before Call
if 'dp-row-actions' in src and 'onclick="toggleRecentDials()"' not in src.split('dp-row-actions', 1)[-1][:400]:
    src = src.replace(
        '<div class="dp-row-actions">\n            <button class="dp-call"',
        '<div class="dp-row-actions">\n            <button class="dp-recent" type="button" onclick="toggleRecentDials()" title="Last 10 numbers you dialed">Recent</button>\n            <button class="dp-call"',
        1,
    )
    print("Added bottom Recent beside Call")
elif 'class="dp-recent"' in src.split('dp-row-actions', 1)[-1][:500] if 'dp-row-actions' in src else False:
    print("Bottom Recent already in row-actions")
else:
    # if Recent only elsewhere, add to row-actions
    if '<button class="dp-recent"' not in src[src.find('dp-row-actions'):src.find('dp-row-actions')+500] if 'dp-row-actions' in src else True:
        if '<div class="dp-row-actions">\n            <button class="dp-call"' in src:
            src = src.replace(
                '<div class="dp-row-actions">\n            <button class="dp-call"',
                '<div class="dp-row-actions">\n            <button class="dp-recent" type="button" onclick="toggleRecentDials()" title="Last 10 numbers you dialed">Recent</button>\n            <button class="dp-call"',
                1,
            )
            print("Added bottom Recent beside Call")

# Ensure list panel exists near dial pad
if 'id="dpRecentList"' not in src:
    src = src.replace(
        'id="dialInput" placeholder="Enter number..." maxlength="20" autocomplete="off" inputmode="tel">\n        <div class="dp-grid">',
        'id="dialInput" placeholder="Enter number..." maxlength="20" autocomplete="off" inputmode="tel">\n        <div id="dpRecentList" class="dp-recent-list" style="display:none" aria-label="Recent dials"></div>\n        <div class="dp-grid">',
        1,
    )
    print("Added dpRecentList")

# CSS if missing
CSS = """
.dp-recent{background:#f1f5f9;color:#334155;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
.dp-recent:hover,.dp-recent.active{background:#e8f0fe;border-color:#93c5fd;color:#0047AB}
.dp-recent-list{margin-top:10px;border:1px solid #e2e8f0;border-radius:10px;background:#fff;max-height:220px;overflow-y:auto}
.dp-recent-item{display:flex;align-items:center;justify-content:space-between;gap:8px;width:100%;padding:10px 12px;border:none;border-bottom:1px solid #f1f5f9;background:transparent;cursor:pointer;text-align:left;font-size:13px;color:#0f172a}
.dp-recent-item:last-child{border-bottom:none}
.dp-recent-item:hover{background:#f8fafc}
.dp-recent-empty{padding:14px;text-align:center;color:#94a3b8;font-size:12px}
"""
if "dp-recent-list" not in src or ".dp-recent{" not in src:
    if ".dp-call{" in src and ".dp-recent{" not in src:
        src = src.replace(".dp-call{", CSS + "\n.dp-call{", 1)
        print("CSS added")

subprocess.run(
    ["docker", "exec", "-i", "skykin-web", "tee", IDX],
    input=src,
    text=True,
    check=True,
    stdout=subprocess.DEVNULL,
)
print("OK: supervisor Recent now at bottom (same as agent)")
subprocess.run(["docker", "exec", "skykin-web", "grep", "-n", "dp-recent\\|dp-row-actions\\|Dial number", IDX], check=False)
