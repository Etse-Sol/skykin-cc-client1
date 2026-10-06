import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=20, allow_agent=False, look_for_keys=False)
_, o, e = c.exec_command("ss -lntp | grep 18081; systemctl is-active skykin-ws-sip")
print(o.read().decode() + e.read().decode())
c.close()
