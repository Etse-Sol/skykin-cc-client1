import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "cat /root/skykin-fs-etc/dialplan/default/00_skykin.xml",
    "echo '==== leftover domain dp ===='",
    "ls -l /root/skykin-fs-etc/dialplan/client1.skykin.local/00_ethio_mobile.xml "
    "/etc/freeswitch/dialplan/client1.skykin.local/00_ethio_mobile.xml 2>&1",
    "echo '==== SIP.xml codec/rtp ===='",
    "grep -nE 'codec|rtp|rtcp|ndlb|ext-rtp|local-net|aggressive|rewrite|media' "
    "/root/skykin-fs-etc/sip_profiles/external/SIP.xml",
    "echo '==== webrtc ua ===='",
    "cat /root/skykin-fs-etc/dialplan/default/00_skykin_webrtc_ua.xml 2>/dev/null; "
    "docker exec skykin-freeswitch cat /etc/freeswitch/dialplan/default/00_skykin_webrtc_ua.xml",
    "echo '==== beep ===='",
    "docker exec skykin-freeswitch sh -c 'ls /usr/share/freeswitch/sounds/en/us/callie/misc/8000/beep.wav "
    "/usr/share/freeswitch/sounds/*/misc/beep.wav 2>/dev/null; find /usr/share/freeswitch/sounds -name beep.wav | head'",
    "echo '==== last outbound ===='",
    "docker exec skykin-freeswitch sh -c \"grep -n 'sofia/gateway/SIP' /var/log/freeswitch/freeswitch.log | tail -8\"",
    "echo '==== leftover content ===='",
    "cat /root/skykin-fs-etc/dialplan/client1.skykin.local/00_ethio_mobile.xml 2>/dev/null | head -40",
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
