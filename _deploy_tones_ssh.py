import sys
from pathlib import Path
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect(
        "196.189.236.140",
        port=30,
        username="root",
        password="Pass@1234",
        timeout=12,
        allow_agent=False,
        look_for_keys=False,
    )
except Exception as e:
    print("SSH_FAIL", e)
    raise SystemExit(1)

sftp = c.open_sftp()
sftp.put(
    str(Path(r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php")),
    "/tmp/index.php",
)
sftp.close()
cmd = (
    "install -m 0644 /tmp/index.php /opt/skykin/app/app/agent_dashboard/index.php; "
    "docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true; "
    "grep -c playOutboundFailTone /opt/skykin/app/app/agent_dashboard/index.php"
)
_, o, e = c.exec_command(cmd, timeout=60)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
print("OK")
