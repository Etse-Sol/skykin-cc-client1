import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOCAL = r"C:\Users\hp\skykin-fusionpbx\patch_bleg_reinvite.py"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
sftp.put(LOCAL, "/tmp/patch_bleg_reinvite.py")
sftp.close()
_, o, e = c.exec_command(
    "python3 /tmp/patch_bleg_reinvite.py; "
    "docker exec skykin-freeswitch fs_cli -x reloadxml; "
    "echo '==== outbound ===='; "
    "grep -n 'bleg_uuid\\|origination_uuid\\|rtcp_audio\\|uuid_media' "
    "/root/skykin-fs-etc/dialplan/default/00_skykin.xml; "
    "pkill -f 'tcpdump -ni enp4s3' || true; "
    "nohup tcpdump -ni enp4s3 -s 0 -w /tmp/ethio.pcap "
    "'udp and net 10.208.233.0/24' "
    "> /tmp/ethio_tcpdump.log 2>&1 & echo capture_pid=$!"
)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
