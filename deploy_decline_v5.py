#!/usr/bin/env python3
import paramiko
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
host = "196.189.236.140"
pw = "Pass@1234"
data = open(r"C:\Users\hp\skykin-fusionpbx\fix_decline_v5.py", "rb").read()
index = open(r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php", "rb").read()

c = None
for port in (30, 8180, 22):
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(
            host,
            port=port,
            username="root",
            password=pw,
            timeout=25,
            look_for_keys=False,
            allow_agent=False,
        )
        print("connected", port)
        break
    except Exception as e:
        print(port, type(e).__name__, e)

if not c:
    raise SystemExit("no ssh")

sftp = c.open_sftp()
with sftp.file("/root/fix_decline_v5.py", "wb") as f:
    f.write(data)
remote = "/opt/skykin/app/app/agent_dashboard/index.php"
with sftp.file(remote + ".bak-from-windows", "wb") as f:
    f.write(index)
with sftp.file(remote, "wb") as f:
    f.write(index)
sftp.close()
print("uploaded fix script + index.php")

cmd = (
    "python3 /root/fix_decline_v5.py; "
    "docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/index.php; "
    "grep -c SKYKIN_SAFE_DECLINE_v3 /opt/skykin/app/app/agent_dashboard/index.php; "
    "grep -c startOutboundPoll /opt/skykin/app/app/agent_dashboard/index.php; "
    "grep -c 'agentHangup && callStartTime' /opt/skykin/app/app/agent_dashboard/index.php"
)
_, o, e = c.exec_command(cmd)
print(o.read().decode())
err = e.read().decode()
if err.strip():
    print(err)
c.close()
print("DONE")
