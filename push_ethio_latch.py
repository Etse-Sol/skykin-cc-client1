import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    username="root",
    password="Pass@1234",
    timeout=25,
    allow_agent=False,
    look_for_keys=False,
)
cmds = r"""
python3 - <<'PY'
from pathlib import Path
old = "rtcp_audio_interval_msec=5000,rtcp_mux=false,rtp_secure_media=false,media_webrtc=false,rtp_advertise_ip=10.0.0.93,include_external_ip=false,ignore_early_media=true"
new = "rtcp_audio_interval_msec=0,rtcp_mux=false,rtp_secure_media=false,media_webrtc=false,rtp_advertise_ip=10.0.0.93,include_external_ip=false,ignore_early_media=false,send_silence_when_idle=100"
pre = '      <action application="set" data="record_stereo=true"/>'
pre2 = '      <action application="pre_answer"/>\n      <action application="set" data="record_stereo=true"/>'
for p in [
    Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml"),
    Path("/root/skykin-fs-etc/dialplan/01_skykin_client1.skykin.local.xml"),
]:
    t = p.read_text()
    n = t.count(old)
    t = t.replace(old, new)
    if pre in t and "pre_answer" not in t:
        t = t.replace(pre, pre2)
    elif 'application="pre_answer"' not in t:
        t = t.replace(
            '      <action application="set" data="call_timeout=60"/>\n',
            '      <action application="set" data="call_timeout=60"/>\n      <action application="pre_answer"/>\n',
        )
    p.write_text(t)
    print(p.name, "bridge_hits", n, "pre_answer", t.count("pre_answer"))
PY
docker exec skykin-freeswitch fs_cli -x reloadxml
echo '==== live outbound ===='
grep -n 'ignore_early\|send_silence\|rtcp_audio\|pre_answer' \
  /root/skykin-fs-etc/dialplan/default/00_skykin.xml | head
"""
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
