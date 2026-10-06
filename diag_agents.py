import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=60):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== extensions in DB ====")
print(run("""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT e.extension, e.number_alias, e.enabled, e.user_context,
       left(e.password, 8) AS pw_start, length(e.password) AS pw_len,
       d.domain_name
FROM v_extensions e
JOIN v_domains d ON d.domain_uuid = e.domain_uuid
ORDER BY e.extension;" """))

print("==== users / groups ====")
print(run("""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT u.username, u.user_enabled, d.domain_name
FROM v_users u
JOIN v_domains d ON d.domain_uuid = u.domain_uuid
ORDER BY u.username;" """))

print("==== live registrations ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))

print("==== lua xml handler / fusionpbx config ====")
print(run("docker exec skykin-freeswitch sh -c 'echo --- lua.conf ---; grep -n xml_handler\\|script-dir\\|lua.conf /etc/freeswitch/autoload_configs/lua.conf.xml | head -40; echo --- fusionpbx ---; cat /etc/fusionpbx/config.conf 2>/dev/null | grep -v password; echo --- modules ---; grep -E \"mod_lua|mod_callcenter|mod_xml\" /etc/freeswitch/autoload_configs/modules.conf.xml'"))

print("==== last register failures ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'sofia_reg|REGISTER|auth fail|FORBIDDEN|NOT FOUND|103|104|105' /var/log/freeswitch/freeswitch.log | tail -40\""))

print("==== last agent-to-agent / local calls ====")
print(run("""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT to_char(start_stamp,'YYYY-MM-DD HH24:MI:SS') AS start,
       caller_id_number, destination_number, hangup_cause, billsec, duration
FROM v_xml_cdr
WHERE destination_number ~ '^[0-9]{3}$' OR caller_id_number ~ '^[0-9]{3}$'
ORDER BY start_stamp DESC
LIMIT 15;" """))

print("==== domain dialplan ====")
print(run("docker exec skykin-freeswitch cat /etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml"))

print("==== default skykin dialplan ====")
print(run("docker exec skykin-freeswitch ls -l /etc/freeswitch/dialplan/default/00_skykin.xml /etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml 2>&1; echo ---; docker exec skykin-freeswitch cat /etc/freeswitch/dialplan/default/00_skykin.xml 2>&1 | head -80"))

print("==== env outbound / domain ====")
print(run("docker exec skykin-freeswitch sh -c 'env | grep -E \"FS_|EXTERNAL_|FUSIONPBX|CDR\" | sort'"))

print("==== recent originate / NO_ROUTE / USER_NOT_REGISTERED ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'NO_ROUTE|USER_NOT_REGISTERED|DESTINATION_OUT_OF_ORDER|INCOMPATIBLE|sofia_contact|EXECUTE.*bridge|Dialplan:.*skykin' /var/log/freeswitch/freeswitch.log | tail -50\""))

c.close()
