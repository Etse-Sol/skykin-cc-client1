#!/usr/bin/env python3
"""Deploy safe decline fix to ecs-cc. Backs up server index.php first."""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "196.189.236.140"
PORTS = (30, 8180, 22, 2222)
LOCAL = Path(r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php")
REMOTE = "/opt/skykin/app/app/agent_dashboard/index.php"
BACKUP = REMOTE + ".bak-safe-rollback"


def connect(password: str) -> paramiko.SSHClient:
    last_err: Exception | None = None
    for port in PORTS:
        print(f"trying SSH {HOST}:{port} ...")
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
                allow_agent=False,
                look_for_keys=False,
            )
            print("connected on", port)
            return c
        except Exception as e:
            last_err = e
            print("fail", port, type(e).__name__, e)
    raise SystemExit("no ssh: " + repr(last_err))


def main() -> None:
    password = getpass.getpass("root password for ecs-cc: ")
    data = LOCAL.read_bytes()
    print("local", LOCAL, len(data), "bytes")

    c = connect(password)
    _, out, err = c.exec_command(
        f"cp -a {REMOTE} {BACKUP} && echo BACKUP_OK && "
        f"grep -c outbound_live {REMOTE} || true"
    )
    print(out.read().decode(errors="replace"))
    print(err.read().decode(errors="replace"))

    sftp = c.open_sftp()
    with sftp.file(REMOTE, "wb") as rf:
        rf.write(data)
    sftp.close()
    print("uploaded", REMOTE)

    checks = (
        f"docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/index.php; "
        f"grep -c startOutboundPoll {REMOTE}; "
        f"grep -c outbound_stop {REMOTE}; "
        f"grep -c outboundFailHard {REMOTE} || true"
    )
    _, out, err = c.exec_command(checks)
    print(out.read().decode(errors="replace"))
    e = err.read().decode(errors="replace")
    if e.strip():
        print(e)
    c.close()
    print()
    print("RESTORE if broken:")
    print(f"  ssh root@{HOST} -p <port> 'cp -a {BACKUP} {REMOTE}'")
    print("DONE")


if __name__ == "__main__":
    main()
