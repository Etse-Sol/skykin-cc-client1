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
old = "rtcp_audio_interval_msec=0,"
new = "rtcp_audio_interval_msec=-1,"
export = '      <action application="export" data="nolocal:execute_on_answer=playback tone_stream://%(600,0,900)"/>\n'
mark = '      <action application="set" data="bleg_uuid=${create_uuid()}"/>\n'
for p in [
    Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml"),
    Path("/root/skykin-fs-etc/dialplan/01_skykin_client1.skykin.local.xml"),
]:
    t = p.read_text()
    t = t.replace(old, new)
    if "execute_on_answer=playback tone_stream" not in t:
        t = t.replace(mark, mark + export)
    p.write_text(t)
    print(p.name, "rtcp-1", t.count("rtcp_audio_interval_msec=-1"), "tone", t.count("tone_stream"))
PY
docker exec skykin-freeswitch fs_cli -x reloadxml
# Arm a 3-minute capture of Ethio media for the next test call
pkill -f 'tcpdump.*ethio-rtp' 2>/dev/null || true
nohup tcpdump -ni enp4s3 -w /tmp/ethio-rtp.pcap \
  'udp and (host 10.208.233.197 or host 10.208.233.203 or host 10.208.233.134)' \
  >/tmp/ethio-rtp.log 2>&1 &
sleep 1
pgrep -af 'tcpdump.*ethio-rtp' | head -3
echo '==== outbound snippet ===='
grep -n 'rtcp_audio\|tone_stream\|ignore_early' /root/skykin-fs-etc/dialplan/default/00_skykin.xml | head
"""
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
