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


def run(cmd, timeout=240):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print(
    run(
        r"""
set -e
XML=/root/skykin-fs-etc/autoload_configs/xml_cdr.conf.xml
python3 - <<'PY'
from pathlib import Path
p = Path("/root/skykin-fs-etc/autoload_configs/xml_cdr.conf.xml")
t = p.read_text()
t = t.replace(
    'http://web/app/xml_cdr/xml_cdr_import.php',
    'http://127.0.0.1:8090/app/xml_cdr/xml_cdr_import.php',
)
p.write_text(t)
print("cdr url -> 127.0.0.1:8090")
print(p.read_text())
PY
docker exec skykin-freeswitch fs_cli -x reloadxml
docker exec skykin-freeswitch fs_cli -x "reload mod_xml_cdr" || true

# Import spooled CDRs into FusionPBX
docker exec skykin-web mkdir -p /var/log/freeswitch/xml_cdr
docker cp skykin-freeswitch:/var/log/freeswitch/xml_cdr/. /tmp/skykin-xml-cdr/
docker cp /tmp/skykin-xml-cdr/. skykin-web:/var/log/freeswitch/xml_cdr/
echo "spool copied: $(ls /tmp/skykin-xml-cdr/*.cdr.xml 2>/dev/null | wc -l) files"
curl -sS -o /tmp/cdr_import.out -w "import_http=%{http_code}\n" \
  -u fusionpbx:fusionpbx -X POST \
  http://127.0.0.1:8090/app/xml_cdr/xml_cdr_import.php --data 'cdr='
# FusionPBX also imports from CLI
docker exec skykin-web php /var/www/fusionpbx/app/xml_cdr/xml_cdr_import.php || true
echo "web spool left: $(docker exec skykin-web sh -c 'ls /var/log/freeswitch/xml_cdr/*.cdr.xml 2>/dev/null | wc -l')"

# Share recordings: copy FS archive into the web volume, then bind it into FS
VOL=/var/lib/docker/volumes/call-center_skykin_recordings/_data
mkdir -p "$VOL/client1.skykin.local/archive"
docker cp skykin-freeswitch:/var/lib/freeswitch/recordings/client1.skykin.local/. \
  "$VOL/client1.skykin.local/"
chmod -R a+rX "$VOL/client1.skykin.local" || true
echo "web archive 13: $(ls "$VOL/client1.skykin.local/archive/2026/Aug/13" 2>/dev/null | wc -l)"

PID=$(docker inspect -f '{{.State.Pid}}' skykin-freeswitch)
if [ -n "$PID" ] && [ "$PID" != "0" ]; then
  nsenter -t "$PID" -m mount --bind "$VOL" /var/lib/freeswitch/recordings
  echo "bound recordings volume into freeswitch pid=$PID"
fi
docker exec skykin-web ls /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13 | wc -l
"""
    )
)
print("==== cdr today after import ====")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT COUNT(*) AS n,
       MIN(to_timestamp(start_epoch)) AS first,
       MAX(to_timestamp(start_epoch)) AS last
FROM v_xml_cdr
WHERE start_epoch >= extract(epoch from current_date);
" """
    )
)
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT to_timestamp(start_epoch) AS t, direction, caller_id_number, destination_number,
       billsec, cc_agent IS NOT NULL AS has_agent, record_name
FROM v_xml_cdr ORDER BY start_epoch DESC LIMIT 12;
" """
    )
)
c.close()
