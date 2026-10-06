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


def run(cmd, timeout=300):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print(
    run(
        r"""
set -e
docker exec skykin-web sh -c 'chown -R www-data:www-data /var/log/freeswitch/xml_cdr; chmod -R a+rX /var/log/freeswitch/xml_cdr'
echo 'before='$(docker exec skykin-web sh -c 'ls /var/log/freeswitch/xml_cdr/*.cdr.xml 2>/dev/null | wc -l')
docker exec skykin-web php /var/www/fusionpbx/app/xml_cdr/xml_cdr_import.php 400
echo 'after='$(docker exec skykin-web sh -c 'ls /var/log/freeswitch/xml_cdr/*.cdr.xml 2>/dev/null | wc -l')
echo 'failed='$(docker exec skykin-web sh -c 'ls /var/log/freeswitch/xml_cdr/failed 2>/dev/null | wc -l')
"""
    )
)
print("==== cdr counts ====")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT date_trunc('day', to_timestamp(start_epoch)) AS day, COUNT(*) 
FROM v_xml_cdr GROUP BY 1 ORDER BY 1 DESC LIMIT 8;
" """
    )
)

print("==== bind recordings ====")
print(
    run(
        r"""
VOL=/var/lib/docker/volumes/call-center_skykin_recordings/_data
PID=$(docker inspect -f '{{.State.Pid}}' skykin-freeswitch)
echo pid=$PID vol_ok=$(test -d "$VOL" && echo yes)
echo dest=$(ls /proc/$PID/root/var/lib/freeswitch/recordings >/dev/null && echo yes)
mount --bind "$VOL" /proc/$PID/root/var/lib/freeswitch/recordings
echo bind_ok=$?
docker exec skykin-freeswitch ls /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13 | wc -l
docker exec skykin-web ls /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13 | wc -l
"""
    )
)
c.close()
