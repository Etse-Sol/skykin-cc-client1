#!/usr/bin/env python3
"""Remove duplicate global outbound functions (keep only inside SIP IIFE)."""
import re
import shutil
from pathlib import Path

INDEX = Path("/opt/skykin/app/app/agent_dashboard/index.php")

def main() -> None:
    t = INDEX.read_text(encoding="utf-8", errors="replace")
    sip = t.find("sipjs.bundle.js")
    if sip < 0:
        print("ERROR: sipjs.bundle.js not found")
        return

    before, after = t[:sip], t[sip:]
    count_before = before.count("function outboundFailHard")

    # Strip duplicate outbound helpers from the pre-SIP script block only.
    patterns = [
        r"\n// Outbound failed/declined:.*?\nfunction outboundFailHard\(.*?\nwindow\.outboundFailHard = outboundFailHard;\n",
        r"\nfunction outboundFailHard\(\) \{.*?\nwindow\.outboundFailHard = outboundFailHard;\n",
        r"\nfunction resetOutboundFail\(\) \{.*?\nwindow\.resetOutboundFail = resetOutboundFail;\n",
        r"\nfunction stopOutboundPoll\(\) \{.*?\n\}\nfunction startOutboundRingUI\(.*?\n\}\n",
        r"\nfunction startOutboundPoll\(ext, dest\) \{.*?\n\}\n",
        r"\nfunction watchOutboundPeer\(s\) \{.*?\n\}\n",
        r"\nfunction detachOutboundAudio\(\) \{.*?\n\}\n",
    ]
    for pat in patterns:
        before = re.sub(pat, "\n", before, count=1, flags=re.DOTALL)

    t = before + after
    shutil.copy2(INDEX, str(INDEX) + ".bak-dedupe-outbound")
    INDEX.write_text(t, encoding="utf-8")

    lines = [i + 1 for i, ln in enumerate(t.splitlines()) if "function outboundFailHard" in ln]
    sip_line = t[: t.find("function outboundFailHard")].count("\n") + 1 if "function outboundFailHard" in t else 0
    print("removed from pre-SIP block:", count_before, "->", before.count("function outboundFailHard"))
    print("outboundFailHard lines:", lines)
    print("sipjs at line:", t[:sip].count("\n") + 1)
    if len(lines) == 1 and lines[0] > t[:sip].count("\n"):
        print("OK: single outboundFailHard inside SIP IIFE")
    else:
        print("WARN: check manually")


if __name__ == "__main__":
    main()
