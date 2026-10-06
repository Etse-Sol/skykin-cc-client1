import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    username="root",
    password="Pass@1234",
    timeout=25,
    allow_agent=False,
    look_for_keys=False,
)
cmds = r"""
AID=64c5f323-cd40-48ef-a97f-22d546be8b57
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set status ${AID} Logged Out"
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c \
  "UPDATE v_call_center_agents SET agent_status = 'Logged Out' WHERE call_center_agent_uuid = '${AID}';"
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c \
  "SELECT agent_name, agent_status FROM v_call_center_agents ORDER BY agent_name;"
echo '==== fs agents ===='
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent list" | cut -d'|' -f1,6,7
echo '==== regs ===='
docker exec skykin-freeswitch fs_cli -x "sofia status profile internal reg" | grep -E 'User:|Status:'
echo '==== queue ===='
docker exec skykin-freeswitch fs_cli -x "callcenter_config queue list" | awk -F'|' 'NR<=2 {print $1,$2}'
"""
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
