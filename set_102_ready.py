import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
uid = "031ab55a-74f4-4c4a-9252-faaa4a1f4e5e"
cmds = [
    f"docker exec skykin-freeswitch fs_cli -x \"callcenter_config agent set status {uid} Available\"",
    f"docker exec skykin-freeswitch fs_cli -x \"callcenter_config agent set state {uid} Waiting\"",
    f"docker exec skykin-freeswitch fs_cli -x \"callcenter_config agent set max_no_answer {uid} 20\"",
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | awk -F'|' '{print $1,$5,$6,$7,$17}'",
    "docker exec skykin-freeswitch fs_cli -x 'sofia_contact */102@client1.skykin.local'",
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
