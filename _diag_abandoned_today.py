#!/usr/bin/env python3
"""Quick abandoned-call diagnosis for 2026-09-19 on ecs-cc."""
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect(
        "196.189.236.140",
        port=30,
        username="root",
        password="Pass@1234",
        timeout=20,
        allow_agent=False,
        look_for_keys=False,
    )
except Exception as e:
    print("SSH_FAIL", type(e).__name__, e)
    raise SystemExit(2)


def run(cmd, timeout=90):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== agent status now ====")
print(run(
    "docker exec skykin-freeswitch fs_cli -p SkykinEslChangeMe1 -x "
    "'callcenter_config agent list' 2>&1 | head -40"
))

print("==== queue / members ====")
print(run(
    "docker exec skykin-freeswitch fs_cli -p SkykinEslChangeMe1 -x "
    "'callcenter_config queue list' 2>&1 | head -20"
))
print(run(
    "docker exec skykin-freeswitch fs_cli -p SkykinEslChangeMe1 -x "
    "'callcenter_config queue list agents ahununu@ahununu' 2>&1 | head -40"
))

print("==== softphone_fail / TEMPORARY / queue wait today ====")
print(run(
    r"""docker exec skykin-freeswitch sh -c "
tail -c 12M /var/log/freeswitch/freeswitch.log 2>/dev/null |
grep -E '2026-09-19' |
grep -E 'skykin softphone_fail|TEMPORARY_FAILURE|queue wait VISIBLE|retry once|outside_business|biz_hours|skykin welcome|NO_AGENT|Abandoned' |
tail -80
" """
))

print("==== CDR abandoned vs answered today (pg) ====")
print(run(
    r"""docker exec skykin-postgres psql -U fusionpbx -d fusionpbx -t -A -F'|' -c "
SELECT
  CASE
    WHEN direction ILIKE '%inbound%' AND COALESCE(billsec,0)=0 AND (cc_agent_bridged IS NULL OR cc_agent_bridged='') THEN 'aband_no_agent'
    WHEN direction ILIKE '%inbound%' AND COALESCE(billsec,0)=0 THEN 'aband_bill0'
    WHEN direction ILIKE '%inbound%' AND COALESCE(billsec,0)>0 THEN 'talked'
    ELSE direction
  END AS bucket,
  count(*)
FROM v_xml_cdr
WHERE start_stamp::date = '2026-09-19'
  AND (destination_number LIKE '251116198%' OR destination_number LIKE '116198%' OR caller_id_number LIKE '251%')
GROUP BY 1
ORDER BY 2 DESC;
" 2>&1 | head -40"""
))

print("==== sample abandoned with agent fields ====")
print(run(
    r"""docker exec skykin-postgres psql -U fusionpbx -d fusionpbx -c "
SELECT start_stamp, caller_id_number, destination_number,
       billsec, duration, hangup_cause,
       left(coalesce(cc_agent,'')||' '||coalesce(cc_agent_bridged,'')||' '||coalesce(last_app,'')||' '||coalesce(last_arg,''), 80) AS tip
FROM v_xml_cdr
WHERE start_stamp::date = '2026-09-19'
  AND direction ILIKE '%inbound%'
  AND destination_number LIKE '%116198%'
ORDER BY start_stamp DESC
LIMIT 25;
" 2>&1 | head -60"""
))

c.close()
