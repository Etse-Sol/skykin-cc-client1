#!/usr/bin/env python3
"""Restore agent dashboard to last 'working ringing' backup on ecs-cc."""
from pathlib import Path
import re
import shutil

P = Path("/opt/skykin/app/app/agent_dashboard/index.php")
DIR = P.parent

# Newest-first candidates; we pick the best-scoring file that exists.
CANDIDATES = [
    "index.php.bak-bleg-gone",      # after decline poll + stopRingback; before bleg-gone/silence/preanswer
    "index.php.bak-decline-final",  # before decline_final (may lack poll — lower priority)
    "index.php.bak-silence",
    "index.php.bak-preanswer",
    "index.php.bak-outbound-live",
    "index.php.bak-final",
]


def score(text: str) -> int:
    s = 0
    # Things that break outbound (auto-drop)
    if "_outPrevCh" in text:
        s -= 20
    if "skykinSilenceEverything" in text and "outboundFailHard" in text:
        s -= 10
    if "wireOutboundRecvMute" in text:
        s -= 5
    if "muteOutboundReceivers(inv)" in text and "onAccept" in text:
        s -= 3
    # Good signs
    if "function stopRingback" in text:
        s += 5
    if "window.stopRingback = stopRingback" in text:
        s += 3
    if "function startRingback" in text:
        s += 3
    if "outbound_live" in text:
        s += 2
    if "Ringing " in text:
        s += 2
    if "startRingback" in text:
        s += 2
    # Too aggressive decline detect
    if "_outHadBleg && d && !d.bleg" in text:
        s -= 4
    if "prevCh >= 2 && ch < 2" in text:
        s -= 15
    return s


def ensure_stop_ringback_exports(text: str) -> str:
    if "function stopRingback" not in text:
        return text
    if "window.stopRingback = stopRingback" in text:
        return text
    m = re.search(r"(function stopRingback\(\) \{.*?\n\})", text, re.DOTALL)
    if not m:
        return text
    insert = m.group(1) + "\nwindow.stopRingback = stopRingback;\nwindow.startRingback = startRingback;\n"
    return text[: m.start()] + insert + text[m.end() :]


def main() -> None:
    shutil.copy2(P, str(P) + ".bak-before-restore")
    best_path = None
    best_score = -999
    for name in CANDIDATES:
        b = DIR / name
        if not b.is_file():
            continue
        t = b.read_text(encoding="utf-8", errors="replace")
        sc = score(t)
        print(f"{name}: score={sc}")
        if sc > best_score:
            best_score = sc
            best_path = b

    if not best_path:
        print("ERROR: no backup files found in", DIR)
        print("Run: ls -la", DIR / "index.php.bak*")
        raise SystemExit(1)

    text = best_path.read_text(encoding="utf-8", errors="replace")
    text = ensure_stop_ringback_exports(text)
    P.write_text(text, encoding="utf-8")
    print("RESTORED FROM:", best_path.name)
    print("stopRingback:", "function stopRingback" in text)
    print("window.stopRingback:", "window.stopRingback = stopRingback" in text)
    print("aggressive drop:", "_outPrevCh" in text or "prevCh >= 2" in text)
    print("outbound_live:", "outbound_live" in text)


if __name__ == "__main__":
    main()
