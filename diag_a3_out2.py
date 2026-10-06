import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n '13:31:00' /var/log/freeswitch/freeswitch.log | grep -E '103|0939777880|Dialplan|bridge|Hangup|DESTINATION|NO_ROUTE|USER_NOT|sofia/gateway|EXECUTE' | head -60" """,
    r"""docker exec skykin-freeswitch sh -c "grep -n 'sofia/internal/103@' /var/log/freeswitch/freeswitch.log | tail -40" """,
    r"""docker exec skykin-freeswitch fs_cli -x 'user_exists id 103 client1.skykin.local'""",
    r"""docker exec skykin-freeswitch fs_cli -x 'user_data 103@client1.skykin.local attr context'""",
    r"""docker exec skykin-freeswitch fs_cli -x 'user_data 103@client1.skykin.local var user_context'""",
    r"""docker exec skykin-freeswitch fs_cli -x 'user_data 103@client1.skykin.local var outbound_caller_id_number'""",
    r"""docker exec skykin-freeswitch fs_cli -x 'user_data 102@client1.skykin.local var user_context'""",
    r"""grep -n '103\|102\|outbound\|09' /root/skykin-fs-etc/dialplan/default/00_skykin.xml | head -40""",
    r"""ls /root/skykin-fs-etc/directory/default/ /root/skykin-fs-etc/directory/ 2>/dev/null; ls /root/skykin-fs-etc/dialplan/default/ | head""",
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
