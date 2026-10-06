#!/usr/bin/env python3
"""Check agent registration / Ready vs abandoned windows on 2026-09-19."""
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


def run(cmd, timeout=120):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== current SIP regs (internal) ====")
print(run(
    "docker exec skykin-freeswitch fs_cli -p SkykinEslChangeMe1 -x "
    "'sofia status profile internal reg' 2>&1 | grep -E 'User:|Contact:|Status|ahununu|201|202|203|204' | head -50"
))

print("==== current callcenter agents ====")
print(run(
    "docker exec skykin-freeswitch fs_cli -p SkykinEslChangeMe1 -x "
    "'callcenter_config agent list' 2>&1 | head -30"
))

print("==== answered vs abandoned today inbound DID ====")
print(run(
    r"""docker exec skykin-postgres psql -U fusionpbx -d fusionpbx -c "
SELECT to_char(start_stamp,'HH24:MI') AS t,
       caller_id_number AS caller,
       billsec,
       hangup_cause,
       coalesce(cc_agent,'') AS cc_agent,
       coalesce(cc_agent_bridged,'') AS bridged,
       left(coalesce(last_arg,''),40) AS last_arg
FROM v_xml_cdr
WHERE start_stamp::date = '2026-09-19'
  AND direction ILIKE 'inbound'
  AND destination_number LIKE '%116198%'
ORDER BY start_stamp;
" 2>&1 | head -80"""
))

print("==== softphone_fail counts by hour ====")
print(run(
    r"""docker exec skykin-freeswitch sh -c '
grep -E "2026-09-19.*(skykin softphone_fail|TEMPORARY_FAILURE|queue wait VISIBLE|callcenter.*Available|agent status)" /var/log/freeswitch/freeswitch.log 2>/dev/null | \
  sed -n "s/.*\([0-9][0-9]:[0-9][0-9]\):[0-9][0-9].*/\1/p" | cut -c1-2 | sort | uniq -c | sort -n
' 2>&1 | tail -40"""
))

print("==== sample softphone_fail lines ====")
print(run(
    r"""docker exec skykin-freeswitch sh -c '
grep "2026-09-19" /var/log/freeswitch/freeswitch.log 2>/dev/null | grep -E "softphone_fail|TEMPORARY_FAILURE" | tail -30
'"""
))

c.close()
