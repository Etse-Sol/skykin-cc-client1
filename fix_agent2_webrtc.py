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


def run(cmd, timeout=80):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print("==== db contacts ====")
print(
    run(
        "docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
        "\"SELECT agent_name, agent_status, agent_contact, agent_max_no_answer "
        "FROM v_call_center_agents ORDER BY agent_name;\""
    )
)
print("==== xml contacts ====")
print(
    run(
        "grep -n -A2 'agent name\\|contact\\|max-no-answer\\|strategy' "
        "/root/skykin-fs-etc/autoload_configs/callcenter.conf.xml | head -80"
    )
)
c.close()
