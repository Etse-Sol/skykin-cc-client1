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


def run(cmd, timeout=90):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print("==== clocks ====")
print(run("date; date -u; docker exec skykin-web php -r 'echo date_default_timezone_get(), \" \", date(\"Y-m-d H:i:s\"), \"\\n\";'"))
print("==== recordings mounts ====")
print(run("docker inspect skykin-web --format '{{json .Mounts}}' | python3 -m json.tool | head -80"))
print(run("docker exec skykin-web ls -la /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13 2>&1 | tail -20"))
print(run("docker exec skykin-freeswitch ls -la /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13 2>&1 | tail -20"))
print("==== cdr today ====")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT COUNT(*) AS n,
       MIN(to_timestamp(start_epoch)) AS first,
       MAX(to_timestamp(start_epoch)) AS last
FROM v_xml_cdr WHERE start_epoch >= extract(epoch from current_date);
" """
    )
)
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT start_stamp, direction, caller_id_number, destination_number, billsec,
       hangup_cause, domain_name, record_path, record_name,
       cc_agent, cc_queue, extension_uuid IS NOT NULL AS has_ext
FROM v_xml_cdr
ORDER BY start_epoch DESC
LIMIT 15;
" """
    )
)
print("==== xml_cdr cols ====")
print(
    run(
        r"""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT column_name FROM information_schema.columns
WHERE table_name='v_xml_cdr'
  AND column_name ~ 'cc_|agent|record|caller|dest|bridge|last_arg|originat'
ORDER BY column_name;
" """
    )
)
print("==== cdr import / xml_cdr logs ====")
print(run("docker exec skykin-freeswitch grep -E 'xml_cdr|CDR' /var/log/freeswitch/freeswitch.log | tail -15"))
print(run("ls /var/log/freeswitch/xml_cdr 2>/dev/null | tail; docker exec skykin-web ls /var/log/freeswitch/xml_cdr 2>/dev/null | tail"))
c.close()
