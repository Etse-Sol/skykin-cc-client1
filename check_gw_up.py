import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
_, o, e = c.exec_command("journalctl -u skykin-ws-sip -n 8 --no-pager")
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
