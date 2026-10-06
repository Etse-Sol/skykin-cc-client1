import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "echo '==== DID ===='; cat /root/skykin-fs-etc/dialplan/public/01_skykin_did.xml",
    "echo '==== CC XML ===='; grep -n 'moh\\|hold\\|queue\\|8000' /root/skykin-fs-etc/autoload_configs/callcenter.conf.xml | head -40",
    "echo '==== CC QUEUE ===='; docker exec skykin-freeswitch fs_cli -x 'callcenter_config queue list' | head -5",
    "echo '==== CC QUEUE 8000 ===='; docker exec skykin-freeswitch fs_cli -x 'callcenter_config queue load 8000@client1.skykin.local'",
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config queue list 8000@client1.skykin.local'",
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
