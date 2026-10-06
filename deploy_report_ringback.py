"""Deploy hunt-leg report filters + inbound ringback / delay tweaks on ecs-cc."""
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "196.189.236.140"
PORT = 30
USER = "root"
PASSWORD = "Pass@1234"
DASH = "/opt/skykin/app/app/agent_dashboard"
LOCAL_DASH = r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard"
ROOT = r"C:\Users\hp\skykin-fusionpbx"

PHP_FILES = [
    "skykin_config.php",
    "index.php",
    "data.php",
    "supervisor.php",
    "reports.php",
]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"connecting {HOST}:{PORT} ...")
c.connect(
    HOST,
    port=PORT,
    username=USER,
    password=PASSWORD,
    timeout=30,
    banner_timeout=30,
    auth_timeout=30,
    allow_agent=False,
    look_for_keys=False,
)

sftp = c.open_sftp()
for name in PHP_FILES:
    local = f"{LOCAL_DASH}/{name}"
    remote = f"{DASH}/{name}"
    with open(local, "rb") as f:
        data = f.read()
    with sftp.file(remote, "wb") as rf:
        rf.write(data)
    print(f"uploaded {name} ({len(data)} bytes)")

sftp.put(f"{ROOT}/add_e164_ahununu.py", "/tmp/add_e164_ahununu.py")
sftp.put(f"{ROOT}/patch_ecs_ringback.sh", "/tmp/patch_ecs_ringback.sh")
sftp.close()

_, out, err = c.exec_command("chmod +x /tmp/patch_ecs_ringback.sh && bash /tmp/patch_ecs_ringback.sh", timeout=120)
print(out.read().decode("utf-8", "replace"))
print(err.read().decode("utf-8", "replace"))
c.close()
print("ALL DONE")
