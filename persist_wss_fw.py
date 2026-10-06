import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
_, out, err = c.exec_command(
    "ufw allow from 172.16.0.0/12 to any port 7443 proto tcp comment 'skykin-wss-from-docker' && "
    "ufw allow from 172.16.0.0/12 to any port 5066 proto tcp comment 'skykin-ws-from-docker' && "
    "ufw status | grep -E '7443|5066'",
    timeout=20,
)
print(out.read().decode(errors="replace") + err.read().decode(errors="replace"))
c.close()
