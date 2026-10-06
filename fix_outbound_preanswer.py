import re
from pathlib import Path

old = '      <action application="answer"/>'
new = '      <action application="pre_answer"/>\n      <action application="sleep" data="400"/>'
names = (
    "skykin_outbound_et_zero",
    "skykin_outbound_et_nozero",
    "skykin_outbound_et_e164",
)

def patch(text: str) -> str:
    def repl(m):
        block = m.group(0)
        return block.replace(old, new, 1)
    for name in names:
        text = re.sub(
            rf'(<extension name="{name}">.*?</extension>)',
            repl,
            text,
            flags=re.S,
        )
    return text

for q in [
    Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml"),
    *Path("/root/skykin-fs-etc/dialplan").glob("**/01_skykin_*.xml"),
]:
    if not q.exists():
        continue
    s = q.read_text()
    n = patch(s)
    if n != s:
        q.write_text(n)
        print("patched", q)
    else:
        print("no outbound answer in", q)
