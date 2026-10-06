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
# Space in status requires quotes; previous unquoted call failed.
cmd = (
    "docker exec skykin-freeswitch fs_cli -x "
    "\"callcenter_config agent set status "
    "64c5f323-cd40-48ef-a97f-22d546be8b57 'Logged Out'\""
)
_, o, e = c.exec_command(cmd)
print("set:", o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
_, o, e = c.exec_command(
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | cut -d'|' -f1,6,7"
)
print(o.read().decode("utf-8", "replace"))
c.close()
