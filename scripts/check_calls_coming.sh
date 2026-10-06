#!/bin/bash
# Are inbound calls coming right now? Read-only.
set -u
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env 2>/dev/null | cut -d= -f2- || true)
FS() {
  if [ -n "${PW:-}" ]; then
    docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1" 2>/dev/null
  else
    docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -x "$1" 2>/dev/null
  fi
}

echo "===== NOW ====="
date -Is
FS "show channels count"
FS "show calls count"
echo
echo "===== Active channels (brief) ====="
FS "show channels" | head -40
echo
echo "===== Registrations ====="
FS "show registrations" | head -30
echo
echo "===== Last 10 inbound INVITEs ====="
docker exec skykin-freeswitch sh -c 'grep "receiving invite from" /var/log/freeswitch/freeswitch.log 2>/dev/null | tail -10'
echo
echo "===== Today CDR count (ahununu hunt DIDs) ====="
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT COUNT(*) AS today_calls,
       SUM(CASE WHEN COALESCE(billsec,0)::int > 0 THEN 1 ELSE 0 END) AS with_talk
FROM v_xml_cdr
WHERE start_stamp::date = CURRENT_DATE
  AND destination_number ~ '11619803[5-9]|8414';
" 2>/dev/null || true
echo "DONE"
