#!/usr/bin/env python3
"""Restore index.php to start-of-day (before outbound decline patches)."""
from pathlib import Path
import shutil

P = Path("/opt/skykin/app/app/agent_dashboard/index.php")
DIR = P.parent

# Oldest backups first = closest to start of today
PREFERRED = [
    "index.php.bak-outbound-live",
    "index.php.bak-final",
    "index.php.bak-decline-final",
]

def clean_enough(text: str) -> bool:
    bad = ["outboundFailHard", "skykinSilenceEverything", "_outPrevCh", "outbound_stop"]
    return not any(x in text for x in bad)


def main() -> None:
    shutil.copy2(P, str(P) + ".bak-before-startofday")
    chosen = None
    for name in PREFERRED:
        b = DIR / name
        if b.is_file():
            t = b.read_text(encoding="utf-8", errors="replace")
            if clean_enough(t):
                chosen = b
                break

    if not chosen:
        # Pick oldest .bak by mtime that looks clean
        backs = sorted(DIR.glob("index.php.bak*"), key=lambda p: p.stat().st_mtime)
        for b in backs:
            t = b.read_text(encoding="utf-8", errors="replace")
            if clean_enough(t) and "outbound_live" not in t:
                chosen = b
                break

    if not chosen:
        print("ERROR: no suitable backup. List:")
        for b in sorted(DIR.glob("index.php.bak*")):
            print(" ", b.name)
        raise SystemExit(1)

    shutil.copy2(chosen, P)
    t = P.read_text(encoding="utf-8", errors="replace")
    print("RESTORED:", chosen.name)
    print("outbound_live:", "outbound_live" in t)
    print("outboundFailHard:", "outboundFailHard" in t)
    print("stats action:", "'action' === 'stats'" in t or "action'] === 'stats'" in t)


if __name__ == "__main__":
    main()
