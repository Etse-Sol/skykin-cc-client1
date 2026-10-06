import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOCAL = r"C:\Users\hp\skykin-fusionpbx\patch_skykin_outbound.py"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
sftp.put(LOCAL, "/tmp/patch_skykin_outbound.py")
sftp.close()
_, o, e = c.exec_command(
    "cp -a /root/skykin-fs-etc/dialplan/default/00_skykin.xml "
    "/root/skykin-fs-etc/dialplan/default/00_skykin.xml.bak-oneway; "
    "python3 /tmp/patch_skykin_outbound.py; "
    "docker exec skykin-freeswitch fs_cli -x reloadxml; "
    "grep -n 'answer\\|ringback\\|sip_late_negotiation\\|bridge' "
    "/root/skykin-fs-etc/dialplan/default/00_skykin.xml"
)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
