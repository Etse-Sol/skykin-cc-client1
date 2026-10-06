import getpass
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
files = [
    (
        r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php",
        "/opt/skykin/app/app/agent_dashboard/index.php",
    ),
    (
        r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\skykin_config.php",
        "/opt/skykin/app/app/agent_dashboard/skykin_config.php",
    ),
    (
        r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\supervisor.php",
        "/opt/skykin/app/app/agent_dashboard/supervisor.php",
    ),
]

password = getpass.getpass("root password for ecs-cc: ")
print("trying 196.189.236.140:30 ...")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    port=30,
    username="root",
    password=password,
    timeout=20,
    banner_timeout=20,
    auth_timeout=20,
    allow_agent=False,
    look_for_keys=False,
)
sftp = c.open_sftp()
for local, remote in files:
    with open(local, "rb") as f:
        data = f.read()
    with sftp.file(remote, "wb") as rf:
        rf.write(data)
    print("uploaded", remote, len(data))
sftp.close()
_, out, _ = c.exec_command(
    "grep -c waitingCallers /opt/skykin/app/app/agent_dashboard/index.php"
)
print("waitingCallers count:", out.read().decode(errors="replace").strip())
c.close()
print("DONE")
