import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "cat /root/skykin-fs-etc/directory/default/104.xml 2>/dev/null || echo NO_104_XML",
    "docker exec skykin-freeswitch fs_cli -x 'user_exists id 104 client1.skykin.local'",
    "docker exec skykin-freeswitch fs_cli -x 'user_data 104@client1.skykin.local var user_context'",
    "docker exec skykin-freeswitch fs_cli -x 'user_data 104@client1.skykin.local var toll_allow'",
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -c \"SELECT agent_name, agent_id, agent_status, call_center_agent_uuid FROM v_call_center_agents ORDER BY agent_id;\"",
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -c \"SELECT username, user_enabled FROM v_users u JOIN v_domains d ON u.domain_uuid=d.domain_uuid WHERE d.domain_name='client1.skykin.local' ORDER BY username;\"",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'",
]
for cmd in cmds:
    print("====", cmd[:100])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
