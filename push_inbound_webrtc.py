import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOCAL = r"C:\Users\hp\skykin-fusionpbx\fix_inbound_webrtc.py"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
sftp.put(LOCAL, "/tmp/fix_inbound_webrtc.py")
sftp.put(r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\skykin_config.php",
         "/opt/call-center-deployement/call-center/app/agent_dashboard/skykin_config.php")
sftp.close()
contact = (
    "[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,"
    "rtp_advertise_ip=196.189.236.140,include_external_ip=true]"
)
cmds = (
    "python3 /tmp/fix_inbound_webrtc.py; "
    "docker exec skykin-freeswitch fs_cli -x reloadxml; "
    "docker exec skykin-freeswitch fs_cli -x "
    f"\"callcenter_config agent set contact 64c5f323-cd40-48ef-a97f-22d546be8b57 '{contact}user/101@client1.skykin.local'\"; "
    "docker exec skykin-freeswitch fs_cli -x "
    f"\"callcenter_config agent set contact 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e '{contact}user/102@client1.skykin.local'\"; "
    "docker exec skykin-freeswitch fs_cli -x "
    f"\"callcenter_config agent set contact cd794b4f-f54e-4110-ba5d-537a034c243c '{contact}user/103@client1.skykin.local'\"; "
    "echo '==== contacts ===='; "
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | cut -d'|' -f1,5,6; "
    "echo '==== did ===='; grep -n 'nolocal\\|callcenter\\|expression' /root/skykin-fs-etc/dialplan/public/01_skykin_did.xml"
)
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
