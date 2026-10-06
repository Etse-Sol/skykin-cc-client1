#!/bin/bash
# Generate inbound complaint report from live CDR on ecs-cc.
# Usage: bash scripts/skykin_inbound_complaint_report.sh > /tmp/inbound_report.txt
set -u
OUT="${1:-/tmp/skykin_inbound_report_$(date -u +%Y%m%d).txt}"

{
echo "SkyKin / Ahununu — Inbound Report"
echo "Generated (UTC): $(date -u)"
echo "Host: $(hostname)"
echo "============================================================"
echo
echo "PLATFORM"
docker ps --format '{{.Names}} {{.Status}}' | grep skykin || true
systemctl is-active skykin-ws-sip 2>/dev/null || true
df -h / /var 2>/dev/null | sed -n '1,3p'
uptime
echo
echo "7D INBOUND KPI"
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
WITH base AS (
  SELECT *,
    COALESCE(
      (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
        OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> '')
        OR (COALESCE(waitsec,0) > 0 AND billsec > waitsec
            AND last_arg ~* 'user/(1[0-9]{2}|2[0-9]{2})@'))
    , false) AS agent_ok,
    (billsec = 0 AND (
        (hangup_cause IN ('ORIGINATOR_CANCEL','NORMAL_CLEARING')
          AND (duration = 0 OR destination_number ~ '11619803[5-9]$'))
        OR (hangup_cause = 'CALL_REJECTED' AND destination_number ~ '11619803[5-9]$')
    )) AS hunt_noise,
    (billsec = 0
      AND hangup_cause IN ('NORMAL_TEMPORARY_FAILURE','NORMAL_CLEARING','NO_ANSWER','USER_BUSY',
                           'CALL_REJECTED','ORIGINATOR_CANCEL','ALLOTTED_TIMEOUT')
      AND (destination_number ~ '^(1[0-9]{2}|2[0-9]{2})$'
           OR last_arg ~* 'user/(1[0-9]{2}|2[0-9]{2})@'
           OR (destination_number ~ '^[a-z0-9]{4,16}$' AND destination_number !~ '^[0-9]+$'))
    ) AS bridge_retry
  FROM v_xml_cdr
  WHERE start_stamp >= now() - interval '7 days'
    AND destination_number ~ '11619803'
    AND LOWER(COALESCE(direction,'')) = 'inbound'
),
r AS (SELECT * FROM base WHERE NOT hunt_noise AND NOT bridge_retry)
SELECT
  COUNT(*) AS reportable,
  COUNT(*) FILTER (WHERE billsec > 0 AND agent_ok) AS answered_agent,
  COUNT(*) FILTER (WHERE billsec > 0 AND NOT agent_ok) AS abandoned_no_agent,
  COUNT(*) FILTER (WHERE billsec = 0) AS missed,
  ROUND(100.0 * COUNT(*) FILTER (WHERE billsec > 0 AND agent_ok) / NULLIF(COUNT(*),0), 1) AS pct_answered,
  ROUND(100.0 * COUNT(*) FILTER (WHERE billsec > 0 AND NOT agent_ok) / NULLIF(COUNT(*),0), 1) AS pct_abandoned
FROM r;
"
echo
echo "ABANDON BEFORE 08 vs 08-18 EAT"
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
WITH a AS (
  SELECT EXTRACT(HOUR FROM start_stamp AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Addis_Ababa') AS h
  FROM v_xml_cdr
  WHERE start_stamp >= now() - interval '7 days'
    AND direction = 'inbound'
    AND destination_number ~ '11619803'
    AND billsec > 0
    AND NOT COALESCE(
      (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
        OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> '')
        OR (COALESCE(waitsec,0) > 0 AND billsec > waitsec
            AND last_arg ~* 'user/(1[0-9]{2}|2[0-9]{2})@'))
    , false)
)
SELECT
  COUNT(*) FILTER (WHERE h < 8) AS before_08,
  COUNT(*) FILTER (WHERE h >= 8 AND h < 18) AS open_08_18,
  COUNT(*) FILTER (WHERE h >= 18) AS after_18,
  COUNT(*) AS abandoned_total
FROM a;
"
echo
echo "RING THEN ABANDON BY CAUSE"
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT hangup_cause, COUNT(*) AS n
FROM v_xml_cdr
WHERE start_stamp >= now() - interval '7 days'
  AND direction = 'inbound'
  AND destination_number ~ '11619803'
  AND billsec > 0
  AND last_arg ~* 'user/(1[0-9]{2}|2[0-9]{2})@'
  AND NOT COALESCE(
    (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
      OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> '')
      OR (COALESCE(waitsec,0) > 0 AND billsec > waitsec
          AND last_arg ~* 'user/(1[0-9]{2}|2[0-9]{2})@'))
  , false)
GROUP BY 1 ORDER BY 2 DESC;
"
echo
echo "RING THEN ABANDON BY AGENT"
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT substring(last_arg from 'user/([0-9]{3})@') AS agent_ext, COUNT(*) AS n
FROM v_xml_cdr
WHERE start_stamp >= now() - interval '7 days'
  AND direction = 'inbound'
  AND destination_number ~ '11619803'
  AND billsec > 0
  AND last_arg ~* 'user/(1[0-9]{2}|2[0-9]{2})@'
  AND NOT COALESCE(
    (cc_agent_bridged ~* '/(1[0-9]{2}|2[0-9]{2})@'
      OR (bridge_uuid IS NOT NULL AND TRIM(COALESCE(bridge_uuid::text,'')) <> '')
      OR (COALESCE(waitsec,0) > 0 AND billsec > waitsec
          AND last_arg ~* 'user/(1[0-9]{2}|2[0-9]{2})@'))
  , false)
GROUP BY 1 ORDER BY 2 DESC;
"
echo
echo "DONE"
} | tee "$OUT"

echo "Wrote: $OUT" >&2
