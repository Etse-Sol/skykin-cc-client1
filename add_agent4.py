import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
uid = "b3867d46-795b-47bd-a933-d90d16f10a75"
contact = (
    "[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,"
    "rtp_advertise_ip=196.189.236.140,include_external_ip=true]"
    "user/104@client1.skykin.local"
)
cmds = [
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -c \"SELECT extension, password, enabled FROM v_extensions WHERE extension IN ('101','102','103','104') ORDER BY extension;\"",
    f"docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent add {uid} callback'",
    f"docker exec skykin-freeswitch fs_cli -x \"callcenter_config agent set contact {uid} '{contact}'\"",
    f"docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent set status {uid} Logged Out'",
    f"docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent set state {uid} Waiting'",
    f"docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent set max_no_answer {uid} 999'",
    f"docker exec skykin-freeswitch fs_cli -x 'callcenter_config tier add 8000@client1.skykin.local {uid} 1 1'",
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | awk -F'|' '{print $1,$5,$6,$7}'",
]
for cmd in cmds:
    print("====", cmd[:110])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
