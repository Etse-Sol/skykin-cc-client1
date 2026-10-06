import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
local = r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
sftp.put(local, "/tmp/index.php")
sftp.close()

def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")

print(run("""
docker cp /tmp/index.php skykin-web:/var/www/fusionpbx/app/agent_dashboard/index.php
cp /tmp/index.php /opt/call-center-deployement/call-center/app/agent_dashboard/index.php
docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/index.php
docker exec skykin-web grep -n "agent_wss\\|7443\\|/wss/\\|instanceId\\|regId" /var/www/fusionpbx/app/agent_dashboard/index.php | head -20
"""))
c.close()
