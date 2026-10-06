import paramiko
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    port=30,
    username="root",
    password="Pass@1234",
    timeout=25,
    allow_agent=False,
    look_for_keys=False,
)

cmds = [
    "docker exec skykin-freeswitch grep -E 'gateway|SIP7|outbound' /etc/freeswitch/dialplan/01_skykin_ahununu.xml | head -50",
    "docker exec skykin-freeswitch ls /etc/freeswitch/sip_profiles/external/",
    "docker exec skykin-freeswitch fs_cli -x 'sofia status gateway'",
    "docker exec skykin-freeswitch sh -c \"grep -h 'gateway name\\|param name=.username\\|param name=.caller-id' /etc/freeswitch/sip_profiles/external/SIP*.xml\"",
    """docker exec skykin-db psql -U fusionpbx -d fusionpbx -t -A -c "
SELECT g.gateway, g.username, g.caller_id_in_from, d.domain_name
FROM v_gateways g
JOIN v_domains d ON g.domain_uuid = d.domain_uuid
WHERE d.domain_name = 'ahununu'
   OR g.gateway ILIKE '%758%'
   OR g.gateway ILIKE '%757%'
ORDER BY d.domain_name, g.gateway;" """,
    "docker exec skykin-freeswitch env | grep -i ahununu || true",
    "grep -i ahununu /opt/skykin/app/.env 2>/dev/null || true",
]

for cmd in cmds:
    print("====", cmd)
    _, o, e = c.exec_command(cmd, timeout=45)
    out = o.read().decode("utf-8", "replace")
    err = e.read().decode("utf-8", "replace")
    print(out)
    if err.strip():
        print("STDERR:", err)

c.close()
