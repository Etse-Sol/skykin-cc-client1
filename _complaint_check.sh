#!/bin/bash
# Complaint themes check — run on ecs-cc as root. Paste output back.
set -u
echo "===== WHEN ====="
date -u

echo
echo "===== LAST 7 DAYS INBOUND SUMMARY (ahununu DIDs) ====="
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT
  COUNT(*) FILTER (WHERE direction = 'inbound') AS inbound,
  COUNT(*) FILTER (
    WHERE direction = 'inbound'
      AND (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
           OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> ''))
  ) AS agent_connected,
  COUNT(*) FILTER (
    WHERE direction = 'inbound'
      AND answer_stamp IS NOT NULL
      AND NOT (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
               OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> ''))
  ) AS answered_ivr_no_agent,
  COUNT(*) FILTER (
    WHERE direction = 'inbound'
      AND answer_stamp IS NOT NULL
      AND (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
           OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> ''))
      AND COALESCE(billsec,0) - COALESCE(waitsec,0) <= 3
  ) AS connected_talk_le_3s,
  ROUND(100.0 * COUNT(*) FILTER (
    WHERE direction = 'inbound'
      AND (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
           OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> ''))
  ) / NULLIF(COUNT(*) FILTER (WHERE direction = 'inbound'), 0), 1) AS pct_connected
FROM v_xml_cdr
WHERE start_stamp >= now() - interval '7 days'
  AND destination_number ~ '11619803';
"

echo
echo "===== LAST 7 DAYS BY DAY ====="
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT
  (start_stamp AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Addis_Ababa')::date AS day_eat,
  COUNT(*) FILTER (WHERE direction = 'inbound') AS inbound,
  COUNT(*) FILTER (
    WHERE direction = 'inbound'
      AND (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
           OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> ''))
  ) AS connected,
  COUNT(*) FILTER (
    WHERE direction = 'inbound'
      AND answer_stamp IS NOT NULL
      AND NOT (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
               OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> ''))
  ) AS ivr_no_agent
FROM v_xml_cdr
WHERE start_stamp >= now() - interval '7 days'
  AND destination_number ~ '11619803'
GROUP BY 1
ORDER BY 1;
"

echo
echo "===== TODAY: IVR ANSWERED BUT NO AGENT (complaint pattern) ====="
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT start_stamp, caller_id_number, destination_number, billsec, waitsec, hangup_cause,
       left(COALESCE(cc_agent_bridged,''),40) AS bridged,
       left(COALESCE(last_arg,''),40) AS last_arg
FROM v_xml_cdr
WHERE start_stamp >= date_trunc('day', now() AT TIME ZONE 'UTC')
  AND direction = 'inbound'
  AND destination_number ~ '11619803'
  AND answer_stamp IS NOT NULL
  AND NOT (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
           OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> ''))
ORDER BY start_stamp DESC
LIMIT 25;
"

echo
echo "===== TODAY: CONNECTED BUT VERY SHORT TALK (<=3s) ====="
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT start_stamp, caller_id_number, destination_number, billsec, waitsec,
       (COALESCE(billsec,0)-COALESCE(waitsec,0)) AS talksec,
       hangup_cause, left(COALESCE(cc_agent_bridged,''),50) AS bridged
FROM v_xml_cdr
WHERE start_stamp >= date_trunc('day', now() AT TIME ZONE 'UTC')
  AND direction = 'inbound'
  AND destination_number ~ '11619803'
  AND (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
       OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> ''))
  AND COALESCE(billsec,0) - COALESCE(waitsec,0) <= 3
ORDER BY start_stamp DESC
LIMIT 20;
"

echo
echo "===== SOFTPHONE / MEDIA FAILS (7d) ====="
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT hangup_cause, COUNT(*) 
FROM v_xml_cdr
WHERE start_stamp >= now() - interval '7 days'
  AND hangup_cause IN (
    'INCOMPATIBLE_DESTINATION','ALLOTTED_TIMEOUT','NORMAL_TEMPORARY_FAILURE',
    'DESTINATION_OUT_OF_ORDER','RECOVERY_ON_TIMER_EXPIRE'
  )
GROUP BY 1 ORDER BY 2 DESC;
"

echo
echo "===== DONE ====="
