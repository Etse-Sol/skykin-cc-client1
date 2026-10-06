import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
sftp.put(r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php",
         "/opt/call-center-deployement/call-center/app/agent_dashboard/index.php")
sftp.put(r"C:\Users\hp\skykin-fusionpbx\skykin_ws_sip.py",
         "/etc/skykin/skykin_ws_sip.py")
sftp.close()
uid103 = "cd794b4f-f54e-4110-ba5d-537a034c243c"
uid102 = "031ab55a-74f4-4c4a-9252-faaa4a1f4e5e"
cmds = (
    "systemctl restart skykin-ws-sip; sleep 1; systemctl is-active skykin-ws-sip; "
    f"docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent set status {uid103} Available'; "
    f"docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent set state {uid103} Waiting'; "
    f"docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent set max_no_answer {uid103} 999'; "
    f"docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent set status {uid102} Available'; "
    f"docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent set state {uid102} Waiting'; "
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | awk -F'|' '{print $1,$6,$7}'"
)
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
