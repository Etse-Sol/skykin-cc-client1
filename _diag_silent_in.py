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
connected = False
for host, user, pw in [
    ("196.189.236.140", "root", "Pass@1234"),
    ("196.189.236.140", "root", "seloema"),
    ("192.168.243.129", "root", "seloema"),
]:
    try:
        c.connect(
            host,
            username=user,
            password=pw,
            timeout=12,
            allow_agent=False,
            look_for_keys=False,
        )
        print("CONNECTED", host, user)
        connected = True
        break
    except Exception as e:
        print("FAIL", host, user, type(e).__name__, e)

if not connected:
    raise SystemExit(1)

uuids = [
    "a0dcefec-947f-4aed-ac4d-1ebca4f16324",
    "d8c1efce-53ac-4713-aebb-55d76c474421",
    "ac5d08bf-1fbd-4542-b15a-b87696db4649",
]

parts = [
    "echo '=== sofia ext-rtp / ice ==='",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | grep -iE 'Ext-RTP|Ext-SIP|RTP-IP|SIP-IP|URL|WS-BINDING'",
    "echo",
    "echo '=== recent registrations ==='",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg' | head -50",
    "echo",
]
for u in uuids:
    parts.append(f"echo '===== UUID {u} ====='")
    parts.append(
        "docker exec skykin-freeswitch sh -c "
        f"\"grep -n '{u}' /var/log/freeswitch/freeswitch.log "
        "| grep -iE 'AUDIO RTP|ICE|DTLS|fingerprint|candidate|Codec|BRIDGE|ANSWER|"
        "Hangup|no suitable|INCOMPATIBLE|secure_media|a=candidate|c=IN|"
        "Auto Changing|Remote audio|Local audio|read=|write=|sofia/internal/"
        " | tail -80\""
    )
    parts.append("echo")

parts.append("echo '=== last media lines ==='")
parts.append(
    "docker exec skykin-freeswitch sh -c "
    "\"grep -E 'AUDIO RTP|Remote audio|Local audio|ICE Negotiated|DTLS|"
    "Codec negotiated|no suitable|INCOMPATIBLE' /var/log/freeswitch/freeswitch.log "
    "| tail -50\""
)

cmd = "\n".join(parts)
_, o, e = c.exec_command(cmd, timeout=120)
print(o.read().decode("utf-8", "replace"))
err = e.read().decode("utf-8", "replace")
if err.strip():
    print("STDERR", err[:1200])
c.close()
