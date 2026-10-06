import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOCAL = r"C:\Users\hp\skykin-fusionpbx\patch_bleg_plain.py"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
sftp.put(LOCAL, "/tmp/patch_bleg_plain.py")
sftp.close()
_, o, e = c.exec_command(
    "python3 /tmp/patch_bleg_plain.py; "
    "docker exec skykin-freeswitch fs_cli -x reloadxml; "
    "echo '==== bridge ===='; "
    "grep -n 'bridge data' /root/skykin-fs-etc/dialplan/default/00_skykin.xml; "
    "echo '==== leftover ===='; "
    "ls -l /root/skykin-fs-etc/dialplan/client1.skykin.local/; "
    "echo '==== 200 SDP ===='; "
    "docker exec skykin-freeswitch sh -c \"sed -n '230040,230090p' /var/log/freeswitch/freeswitch.log\""
)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
