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
sftp = c.open_sftp()
sftp.put(r"C:\Users\hp\skykin-fusionpbx\finish_cdr_rec.sh", "/tmp/finish_cdr_rec.sh")
sftp.close()
_, o, e = c.exec_command("chmod +x /tmp/finish_cdr_rec.sh && /tmp/finish_cdr_rec.sh", timeout=120)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
