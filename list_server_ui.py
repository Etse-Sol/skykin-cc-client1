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
    "find /opt/call-center-deployement/call-center/app/agent_dashboard "
    "-maxdepth 2 -type f "
    "\\( -name '*.php' -o -name '*.js' -o -name '*.css' \\) "
    "| sort; echo '----'; ls -la /opt/call-center-deployement/call-center/app/agent_dashboard"
)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
