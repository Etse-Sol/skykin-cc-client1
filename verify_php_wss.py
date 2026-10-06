import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
_, out, err = c.exec_command(
    "docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/index.php; "
    "docker exec skykin-web grep -n \"agent_wss\\|wss://\" /var/www/fusionpbx/app/agent_dashboard/index.php | head -8")
print(out.read().decode(errors="replace") + err.read().decode(errors="replace"))
c.close()
