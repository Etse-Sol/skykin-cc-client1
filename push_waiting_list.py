import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
host = "196.189.236.140"
files = [
    (
        r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php",
        "/opt/call-center-deployement/call-center/app/agent_dashboard/index.php",
    ),
    (
        r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\skykin_config.php",
        "/opt/call-center-deployement/call-center/app/agent_dashboard/skykin_config.php",
    ),
    (
        r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\supervisor.php",
        "/opt/call-center-deployement/call-center/app/agent_dashboard/supervisor.php",
    ),
]

def try_ssh(port):
    print(f"trying SSH {host}:{port} ...")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(
        host,
        port=port,
        username="root",
        password="Pass@1234",
        timeout=20,
        banner_timeout=20,
        auth_timeout=20,
        allow_agent=False,
        look_for_keys=False,
    )
    return c

c = None
last_err = None
for port in (8180, 22, 2222, 443):
    try:
        c = try_ssh(port)
        print("connected on", port)
        break
    except Exception as e:
        last_err = e
        print("fail", port, type(e).__name__, e)

if c is None:
    raise SystemExit("no ssh: " + repr(last_err))

sftp = c.open_sftp()
for local, remote in files:
    with open(local, "rb") as f:
        data = f.read()
    with sftp.file(remote, "wb") as rf:
        rf.write(data)
    print("uploaded", remote, len(data))
sftp.close()
_, out, err = c.exec_command(
    "grep -c waitingCallers /opt/call-center-deployement/call-center/app/agent_dashboard/index.php; "
    "docker exec skykin-web grep -c waitingCallers /var/www/fusionpbx/app/agent_dashboard/index.php 2>/dev/null || echo container-miss"
)
print(out.read().decode(errors="replace"))
print(err.read().decode(errors="replace"))
c.close()
print("DONE")
