import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'",
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list'",
    "grep -n 'skykin_outbound\\|answer\\|pre_answer\\|context' /root/skykin-fs-etc/dialplan/01_skykin_client1.skykin.local.xml | head -40",
    "ls /root/skykin-fs-etc/dialplan/client1.skykin.local/ 2>/dev/null",
    "docker exec skykin-freeswitch fs_cli -x 'user_data 101@client1.skykin.local var user_context'",
    "docker exec skykin-freeswitch fs_cli -x 'user_data 102@client1.skykin.local var user_context'",
    "docker exec skykin-freeswitch fs_cli -x 'user_data 103@client1.skykin.local var user_context'",
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
