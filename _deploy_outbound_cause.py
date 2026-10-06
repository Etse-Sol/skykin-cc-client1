#!/usr/bin/env python3
"""Deploy outbound Busy/switched-off labels + ringback to ecs-cc."""
import sys
from pathlib import Path

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\Users\hp\skykin-fusionpbx")
INDEX = ROOT / "app" / "agent_dashboard" / "index.php"
LUA = ROOT / "docker" / "freeswitch" / "scripts" / "skykin_outbound.lua"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    port=30,
    username="root",
    password="Pass@1234",
    timeout=25,
    allow_agent=False,
    look_for_keys=False,
)


def run(cmd, timeout=120):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    text = out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")
    print(text)
    return text


sftp = c.open_sftp()
sftp.put(str(INDEX), "/tmp/index.php.outbound_cause")
sftp.put(str(LUA), "/tmp/skykin_outbound.lua")
sftp.close()

print("==== install index.php ====")
run(
    "install -m 0644 /tmp/index.php.outbound_cause "
    "/opt/skykin/app/app/agent_dashboard/index.php && "
    "grep -c skykinOutboundFailLabel /opt/skykin/app/app/agent_dashboard/index.php && "
    "grep -c hangup_cause /opt/skykin/app/app/agent_dashboard/index.php && "
    "docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true"
)

print("==== install skykin_outbound.lua ====")
run(
    "mkdir -p /opt/skykin/fs-live && "
    "cp /tmp/skykin_outbound.lua /opt/skykin/fs-live/skykin_outbound.lua && "
    "cp /tmp/skykin_outbound.lua /opt/skykin/fs-config/skykin_outbound.lua 2>/dev/null || true && "
    "docker cp /tmp/skykin_outbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_outbound.lua && "
    "docker exec skykin-freeswitch grep -n 'Propagate the real B-leg\\|hangup agent cause' "
    "/etc/freeswitch/scripts/skykin_outbound.lua | head -5"
)

print("==== DONE ====")
c.close()
