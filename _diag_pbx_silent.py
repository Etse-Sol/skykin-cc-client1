#!/usr/bin/env python3
import sys
try:
    import paramiko
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ok = False
for host, user, pw in [
    ("196.189.236.140", "root", "Pass@1234"),
    ("196.189.236.126", "root", "Pass@1234"),
    ("196.189.236.140", "root", "seloema"),
]:
    try:
        c.connect(host, username=user, password=pw, timeout=12,
                  allow_agent=False, look_for_keys=False)
        print("CONNECTED", host)
        ok = True
        break
    except Exception as e:
        print("FAIL", host, type(e).__name__, e)
if not ok:
    sys.exit(1)

cmd = r'''
echo "=== containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}" | head -20
echo
echo "=== FS uptime / sofia ==="
docker exec skykin-freeswitch fs_cli -x "status" 2>&1 | head -15
docker exec skykin-freeswitch fs_cli -x "sofia status" 2>&1 | head -25
echo
echo "=== opening/music files ==="
docker exec skykin-freeswitch sh -c '
  for f in opening-long.wav opening.wav welcome.wav music.wav waiting-2.wav; do
    ls -la /var/lib/freeswitch/recordings/ahununu/$f 2>/dev/null || echo "MISSING $f"
  done
'
echo
echo "=== last inbound notices ==="
docker exec skykin-freeswitch sh -c '
  grep -E "skykin (inbound answer|opening|ringback|music|after-hours|inbound try|queue wait)" /var/log/freeswitch/freeswitch.log | tail -40
'
echo
echo "=== last 3 external inbound RTP/answer ==="
docker exec skykin-freeswitch sh -c '
  grep -E "sofia/external/\+251.*(AUDIO RTP|has been answered|Pre-Answer)|Codec Activated|streamFile|playback" /var/log/freeswitch/freeswitch.log | tail -40
'
echo
echo "=== agents reg ==="
docker exec skykin-freeswitch fs_cli -x "sofia status profile internal reg" 2>&1 | head -30
echo
echo "=== lua media line ==="
docker exec skykin-freeswitch grep -n "rtp_secure_media\|opening_path\|streamFile\|answer" /etc/freeswitch/scripts/skykin_inbound.lua | head -25
'''
_, o, e = c.exec_command(cmd, timeout=90)
print(o.read().decode("utf-8", "replace"))
err = e.read().decode("utf-8", "replace")
if err.strip():
    print("STDERR", err[:800])
c.close()
