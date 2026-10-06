from pathlib import Path
p = Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml")
t = p.read_text()
old_ans = (
    '      <action application="answer"/>\n'
    '      <action application="set" data="ringback=${us-ring}"/>\n'
    '      <action application="set" data="instant_ringback=true"/>\n'
)
if old_ans not in t:
    raise SystemExit("answer/ringback block not found")
t = t.replace(old_ans, "")
old_br = "ignore_early_media=true,origination_caller_id_number="
new_br = "ignore_early_media=true,sip_late_negotiation=true,origination_caller_id_number="
if old_br not in t:
    raise SystemExit("bridge vars not found")
t = t.replace(old_br, new_br)
p.write_text(t)
print("patched bridges", t.count("sip_late_negotiation=true"))
print("answer left", t.count('application="answer"'))
