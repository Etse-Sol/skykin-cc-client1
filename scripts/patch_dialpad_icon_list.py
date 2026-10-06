#!/usr/bin/env python3
"""Match dial pad: Recent list BELOW buttons; Call = green phone icon only.
Patches agent index.php + supervisor.php on skykin-web."""
import subprocess
import re
import sys

def load(path):
    return subprocess.check_output(["docker", "exec", "skykin-web", "cat", path], text=True, errors="replace")

def save(path, src):
    subprocess.run(
        ["docker", "exec", "-i", "skykin-web", "tee", path],
        input=src, text=True, check=True, stdout=subprocess.DEVNULL,
    )

def patch_call_icon(src, label):
    n = 0
    src2, c = re.subn(
        r'(<button class="dp-call"[^>]*>)\s*(?:&#128222;|&amp;#128222;|📞)?\s*&nbsp;\s*Call\s*(</button>)',
        r'\1&#128222;\2',
        src,
        count=3,
    )
    n += c
    src = src2
    src2, c = re.subn(
        r'(<button class="dp-call"[^>]*>)&#128222;&nbsp; Call(</button>)',
        r'\1&#128222;\2',
        src,
        count=3,
    )
    n += c
    src = src2
    # plain text Call
    src2, c = re.subn(
        r'(<button class="dp-call"[^>]*>)[^<]*Call[^<]*(</button>)',
        r'\1&#128222;\2',
        src,
        count=2,
    )
    if 'dp-call' in src and '&#128222;</button>' not in src[src.find('dp-call'):src.find('dp-call')+200]:
        src = src2
        n += c
    else:
        # if already icon-only, skip destructive replace
        if '&#128222;&nbsp; Call' in src or '📞 Call' in src or (re.search(r'dp-call[^>]*>\s*Call\s*<', src)):
            src = src2
            n += c
    # CSS: round green icon button
    if "border-radius: 50%" not in src and "border-radius:50%" not in src.split(".dp-call", 1)[-1][:300]:
        # agent style block
        src = src.replace(
            "border-radius: 24px; min-height: 44px;\n    padding: 10px 18px; font-size: 14px; font-weight: 700; cursor: pointer;",
            "border-radius: 50%; width: 52px; height: 52px; min-height: 52px;\n    padding: 0; font-size: 22px; font-weight: 700; cursor: pointer; justify-self: center;\n    display: inline-flex; align-items: center; justify-content: center;",
            1,
        )
        # supervisor compact css
        src = src.replace(
            ".dp-call{flex:1;background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;border:none;border-radius:12px;padding:12px;font-size:14px;font-weight:700;cursor:pointer}",
            ".dp-call{width:52px;height:52px;flex:0 0 52px;background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;border:none;border-radius:50%;padding:0;font-size:22px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;box-shadow:0 5px 12px rgba(34,197,94,.22)}",
            1,
        )
        n += 1
    print(f"  {label}: call icon tweaks={n}")
    return src

def move_recent_list_below(src, label):
    """Ensure dpRecentList is after dp-row-actions (below buttons), not above keypad."""
    if 'id="dpRecentList"' not in src:
        print(f"  {label}: no dpRecentList")
        return src
    # Remove existing list wherever it is
    src2 = re.sub(
        r'\s*<div id="dpRecentList"[^>]*>\s*</div>\s*',
        '\n',
        src,
        count=2,
    )
    # Insert after dp-row-actions closing </div>
    # Find dp-row-actions block end
    i = src2.find('class="dp-row-actions"')
    if i < 0:
        print(f"  {label}: no dp-row-actions")
        return src
    # find the closing </div> of row-actions — simple: after first </div> following dp-del or last button in block
    j = src2.find('</div>', i)
    # might be nested; find after dp-del button's parent close
    # Look for pattern: dp-row-actions ... </div> then maybe dp-grid already closed
    k = i
    depth = 0
    started = False
    while k < len(src2):
        if src2.startswith('<div', k):
            depth += 1
            started = True
            k += 4
            continue
        if src2.startswith('</div>', k):
            depth -= 1
            k += 6
            if started and depth == 0:
                break
            continue
        k += 1
    insert = '\n        <div id="dpRecentList" class="dp-recent-list" style="display:none" aria-label="Recent dials"></div>'
    src2 = src2[:k] + insert + src2[k:]
    print(f"  {label}: recent list moved below buttons")
    return src2

# Force call button content to icon only more carefully
def force_icon_button(src):
    src = src.replace('&#128222;&nbsp; Call</button>', '&#128222;</button>')
    src = src.replace('📞&nbsp; Call</button>', '&#128222;</button>')
    src = src.replace('> Call</button>', '>&#128222;</button>')  # too broad?
    # only dp-call
    src = re.sub(
        r'(class="dp-call"[^>]*>)\s*&#128222;\s*&nbsp;\s*Call\s*',
        r'\1&#128222;',
        src,
    )
    src = re.sub(
        r'(class="dp-call"[^>]*>)\s*Call\s*',
        r'\1&#128222;',
        src,
    )
    return src

AGENT = "/var/www/fusionpbx/app/agent_dashboard/index.php"
SUP = "/var/www/fusionpbx/app/agent_dashboard/supervisor.php"

for path, label in [(AGENT, "agent"), (SUP, "supervisor")]:
    print("===", label, "===")
    src = load(path)
    src = force_icon_button(src)
    src = patch_call_icon(src, label)
    src = move_recent_list_below(src, label)
    # title attribute on call
    src = src.replace(
        'class="dp-call" onclick="dpCall()">&#128222;</button>',
        'class="dp-call" onclick="dpCall()" title="Start call" aria-label="Call">&#128222;</button>',
    )
    src = src.replace(
        'class="dp-call" onclick="dpCall()" title="Start call">&#128222;</button>',
        'class="dp-call" onclick="dpCall()" title="Start call" aria-label="Call">&#128222;</button>',
    )
    save(path, src)
    subprocess.run(["docker", "exec", "skykin-web", "grep", "-n", "dpRecentList\\|dp-call\\|dp-row-actions", path], check=False)
    print()

print("OK. Hard refresh agent + supervisor (Ctrl+Shift+R).")
print("Expect: Recent | green phone icon | delete — list opens BELOW those buttons.")
