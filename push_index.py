import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOCAL = r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
with open(LOCAL, "rb") as f:
    data = f.read()
with sftp.file("/opt/call-center-deployement/call-center/app/agent_dashboard/index.php", "wb") as rf:
    rf.write(data)
sftp.close()
print("uploaded", len(data))
c.close()
