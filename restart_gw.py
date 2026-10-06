import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOCAL = r"C:\Users\hp\skykin-fusionpbx\skykin_ws_sip.py"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
with open(LOCAL, "rb") as f:
    data = f.read()
with sftp.file("/etc/skykin/skykin_ws_sip.py", "wb") as rf:
    rf.write(data)
sftp.close()
_, o, e = c.exec_command("systemctl restart skykin-ws-sip; sleep 1; systemctl is-active skykin-ws-sip")
print(o.read().decode() + e.read().decode())
print("uploaded", len(data))
c.close()
