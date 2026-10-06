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
_, o, e = c.exec_command(
    """
docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/skykin_config.php
docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/index.php
docker exec skykin-web php -r '
require "/var/www/fusionpbx/app/agent_dashboard/skykin_config.php";
$p = skykin_recording_path("2f12f335-4405-49d7-b649-9087fe775eb6.wav", "client1.skykin.local", "/var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13");
echo "path=$p playable=".(skykin_recording_playable($p)?"yes":"no")." tz=".skykin_timezone()." now=".date("Y-m-d H:i:s")."\\n";
'
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "SELECT COUNT(*) AS agent2_today FROM v_xml_cdr WHERE start_epoch >= extract(epoch from TIMESTAMP '2026-08-13 00:00:00') AND (caller_id_number='102' OR destination_number='102' OR (cc_agent='031ab55a-74f4-4c4a-9252-faaa4a1f4e5e' AND destination_number ~ '^[+0-9]{3,}$'));"
""",
    timeout=60,
)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
