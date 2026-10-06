#!/usr/bin/env python3
import paramiko
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect(
        "196.189.236.140",
        port=30,
        username="root",
        password="Pass@1234",
        timeout=15,
        allow_agent=False,
        look_for_keys=False,
    )
except Exception as e:
    print("SSH_FAIL", e)
    raise SystemExit(1)

_, o, e = c.exec_command(
    "echo FILE; ls -la /opt/skykin/app/app/agent_dashboard/index.php; "
    "echo V3; grep -c SKYKIN_OUT_RING_v3 /opt/skykin/app/app/agent_dashboard/index.php; "
    "echo RINGING_COLON; grep -c 'Ringing:' /opt/skykin/app/app/agent_dashboard/index.php; "
    "echo LUA; docker exec skykin-freeswitch grep -c Ethio-calibrated /etc/freeswitch/scripts/skykin_outbound.lua || true"
)
print(o.read().decode("utf-8", "replace"))
print(e.read().decode("utf-8", "replace"))
c.close()
