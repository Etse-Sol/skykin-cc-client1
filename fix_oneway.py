import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmd = r'''
set -e
F=/root/skykin-fs-etc/dialplan/default/00_skykin.xml
cp -a "$F" "${F}.bak-oneway"
python3 - <<'PY'
from pathlib import Path
p = Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml")
t = p.read_text()
# Do not answer the WebRTC leg before the mobile answers. Local ringback
# is generated in the browser on 180. Answering first pushed L16 ringback
# and restarted the carrier RTP SSRC on 200, which Ethio then did not play.
old_ans = '''      <action application="answer"/>
      <action application="set" data="ringback=${us-ring}"/>
      <action application="set" data="instant_ringback=true"/>
'''
if old_ans not in t:
    raise SystemExit('answer/ringback block not found')
t = t.replace(old_ans, '')
old_br = 'ignore_early_media=true,origination_caller_id_number='
new_br = 'ignore_early_media=true,sip_late_negotiation=true,origination_caller_id_number='
if old_br not in t:
    raise SystemExit('bridge vars not found')
t = t.replace(old_br, new_br)
p.write_text(t)
print('patched', t.count('sip_late_negotiation=true'), 'bridges')
print('answer_left', t.count('application="answer"'))
PY
docker exec skykin-freeswitch fs_cli -x 'reloadxml'
echo OK
grep -n 'answer\|ringback\|sip_late_negotiation\|bridge' /root/skykin-fs-etc/dialplan/default/00_skykin.xml | head -40
'''
_, o, e = c.exec_command(cmd)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
