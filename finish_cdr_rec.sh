#!/bin/sh
set -e
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c \
  "SELECT to_timestamp(start_epoch) AS t, direction, caller_id_number, destination_number, billsec, left(coalesce(cc_agent,''),8) AS agent, record_name FROM v_xml_cdr WHERE start_epoch >= extract(epoch from TIMESTAMP '2026-08-13') ORDER BY start_epoch DESC LIMIT 15;"

python3 - <<'PY'
import os
d = "/var/lib/docker/volumes/call-center_skykin_recordings/_data/client1.skykin.local/archive/2026/Aug/13"
uuids = [fn[:-4] for fn in os.listdir(d) if fn.endswith(".wav")]
vals = ",".join("('%s')" % u for u in uuids)
sql = """
UPDATE v_xml_cdr c
SET record_path = '/var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13',
    record_name = c.xml_cdr_uuid::text || '.wav'
WHERE c.xml_cdr_uuid::text IN (SELECT u FROM (VALUES %s) AS t(u))
  AND (c.record_name IS NULL OR c.record_name = '');
SELECT COUNT(*) FILTER (WHERE record_name IS NOT NULL AND record_name <> '') AS with_rec,
       COUNT(*) AS total
FROM v_xml_cdr
WHERE start_epoch >= extract(epoch from TIMESTAMP '2026-08-13');
""" % vals
open("/tmp/link_rec.sql", "w").write(sql)
print("uuids", len(uuids))
PY
docker cp /tmp/link_rec.sql skykin-db:/tmp/link_rec.sql
docker exec skykin-db psql -U fusionpbx -d fusionpbx -f /tmp/link_rec.sql

cat > /usr/local/sbin/skykin-sync-recordings.sh <<'SH'
#!/bin/sh
VOL=/var/lib/docker/volumes/call-center_skykin_recordings/_data/client1.skykin.local
mkdir -p "$VOL/archive"
docker cp skykin-freeswitch:/var/lib/freeswitch/recordings/client1.skykin.local/archive/. \
  "$VOL/archive/" >/dev/null 2>&1 || true
chmod -R a+rX "$VOL/archive" 2>/dev/null || true
SH
chmod +x /usr/local/sbin/skykin-sync-recordings.sh
(crontab -l 2>/dev/null | grep -v skykin-sync-recordings; echo '* * * * * /usr/local/sbin/skykin-sync-recordings.sh') | crontab -
echo cron_installed
