#!/bin/bash
# Fraud / attack log check — read-only. Run on ecs-cc as root.
set -u
echo "===== AUTH FAIL / REGISTER FAIL (FS log) ====="
docker exec skykin-freeswitch sh -c 'grep -Ehi "auth fail|authentication failed|wrong password|Invalid password|Cannot authenticate|Rejected by acl|Forbidden" /var/log/freeswitch/freeswitch.log 2>/dev/null | tail -n 80' || true
echo
echo "===== COUNT auth-related lines ====="
docker exec skykin-freeswitch sh -c 'grep -Ehic "auth fail|authentication failed|wrong password|Invalid password|Cannot authenticate|Rejected by acl" /var/log/freeswitch/freeswitch.log 2>/dev/null' || echo 0
echo
echo "===== Registrations now ====="
docker exec skykin-freeswitch fs_cli -x "show registrations" 2>/dev/null | head -n 50 || true
echo
echo "===== Gateways ====="
docker exec skykin-freeswitch fs_cli -x "sofia status gateway" 2>/dev/null | head -n 40 || true
echo
echo "===== Today destinations (top) ====="
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT LEFT(COALESCE(destination_number,''), 24) AS dest,
       COUNT(*) AS calls,
       SUM(CASE WHEN COALESCE(billsec,0)::int > 0 THEN 1 ELSE 0 END) AS answered,
       SUM(COALESCE(billsec,0)::int) AS talk_sec
FROM v_xml_cdr
WHERE start_stamp::date = CURRENT_DATE
GROUP BY 1
ORDER BY calls DESC
LIMIT 30;" 2>/dev/null || echo "CDR query failed"
echo
echo "===== Possible non-Ethiopia destinations (last 3 days) ====="
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT start_stamp, direction, caller_id_number, destination_number, billsec, hangup_cause
FROM v_xml_cdr
WHERE start_stamp::date >= CURRENT_DATE - 2
  AND destination_number ~ '^[+]?[0-9]{8,}$'
  AND destination_number !~ '^(\\+?251|0?9|0?11|8000|20[0-9])'
ORDER BY start_stamp DESC
LIMIT 40;" 2>/dev/null || true
echo
echo "===== Blacklist drops ====="
docker exec skykin-freeswitch sh -c 'grep -F "skykin blacklist drop" /var/log/freeswitch/freeswitch.log 2>/dev/null | tail -n 30' || true
echo
echo "===== FS container auth/scan (24h) ====="
docker logs skykin-freeswitch --since 24h 2>&1 | grep -Ehi 'auth fail|wrong password|forbidden|Invalid password|blacklist drop|Rejected by acl' | tail -n 60 || true
echo
echo "===== SSH failed logins ====="
(grep -Ehi 'Failed password|Invalid user|authentication failure' /var/log/auth.log /var/log/secure 2>/dev/null | tail -n 40) \
  || (journalctl -u ssh --since '24 hours ago' --no-pager 2>/dev/null | grep -Ehi 'Failed|Invalid' | tail -n 40) \
  || echo '(no auth log)'
echo
echo "===== Hangup causes today ====="
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT hangup_cause, COUNT(*) FROM v_xml_cdr
WHERE start_stamp::date = CURRENT_DATE
GROUP BY 1 ORDER BY 2 DESC LIMIT 20;" 2>/dev/null || true
echo
echo "DONE"
