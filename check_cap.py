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
_, o, e = c.exec_command(
    "pgrep -af tcpdump; ls -l /tmp/ethio-rtp.pcap /tmp/ethio-rtp.log 2>&1; "
    "tail -5 /tmp/ethio-rtp.log 2>&1; "
    "which tcpdump; "
    "grep -n 'tone_stream\\|rtcp_audio_interval_msec=-1' "
    "/root/skykin-fs-etc/dialplan/default/00_skykin.xml | head"
)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
