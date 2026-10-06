#!/usr/bin/env python3
"""Upload fixed index.php to ecs-cc and verify both host + container paths."""
import getpass
import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "196.189.236.140"
PORTS = (30, 8180, 22)
LOCAL = r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php"
REMOTE = "/opt/skykin/app/app/agent_dashboard/index.php"
BACKUP = REMOTE + ".bak-upload-v3"


def connect(password: str) -> paramiko.SSHClient:
    last = None
    for port in PORTS:
        print(f"trying {HOST}:{port} ...")
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            c.connect(
                HOST,
                port=port,
                username="root",
                password=password,
                timeout=25,
                banner_timeout=25,
                auth_timeout=25,
                look_for_keys=False,
                allow_agent=False,
            )
            print("connected on", port)
            return c
        except Exception as e:
            last = e
            print("fail:", e)
    raise SystemExit(f"SSH failed: {last}")


def main() -> None:
    data = open(LOCAL, "rb").read()
    print("local bytes:", len(data))
    pw = getpass.getpass("root password for ecs-cc: ")
    c = connect(pw)
    sftp = c.open_sftp()
    try:
        sftp.stat(REMOTE)
        c.exec_command(f"cp -a {REMOTE} {BACKUP}")
        print("backup:", BACKUP)
    except OSError:
        print("WARN: remote missing?", REMOTE)
    with sftp.file(REMOTE, "wb") as rf:
        rf.write(data)
    sftp.close()
    print("uploaded", REMOTE)

    cmd = (
        f"wc -c {REMOTE}; "
        f"grep -c SKYKIN_SAFE_DECLINE_v3 {REMOTE}; "
        f"grep -c 'agentHangup && callStartTime' {REMOTE}; "
        f"grep -c partnerGone {REMOTE}; "
        "docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/index.php; "
        "docker exec skykin-web grep -c SKYKIN_SAFE_DECLINE_v3 /var/www/fusionpbx/app/agent_dashboard/index.php; "
        "docker exec skykin-web grep -c partnerGone /var/www/fusionpbx/app/agent_dashboard/index.php"
    )
    _, out, err = c.exec_command(cmd)
    print(out.read().decode(errors="replace"))
    e = err.read().decode(errors="replace")
    if e.strip():
        print(e)
    c.close()
    print("DONE — Ctrl+Shift+R in browser")


if __name__ == "__main__":
    main()
