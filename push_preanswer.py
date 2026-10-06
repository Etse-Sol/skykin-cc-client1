import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
sftp.put(r"C:\Users\hp\skykin-fusionpbx\fix_outbound_preanswer.py",
         "/tmp/fix_outbound_preanswer.py")
sftp.close()
_, o, e = c.exec_command(
    "python3 /tmp/fix_outbound_preanswer.py; "
    "docker exec skykin-freeswitch fs_cli -x reloadxml; "
    "grep -n 'pre_answer\\|skykin_outbound' /root/skykin-fs-etc/dialplan/default/00_skykin.xml | head -20"
)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
