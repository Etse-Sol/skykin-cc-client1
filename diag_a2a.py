import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=50):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== registrations ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))

print("==== channels ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'show channels'"))

print("==== last local CDRs ====")
print(run("""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT to_char(start_stamp,'HH24:MI:SS') AS t,
       caller_id_number, destination_number, hangup_cause, billsec, duration
FROM v_xml_cdr
ORDER BY start_stamp DESC LIMIT 12;" """))

print("==== last originate / bridge / hangup ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'webrtc_local|skykin_local|USER_NOT_REGISTERED|NO_ROUTE|INCOMPATIBLE|DESTINATION_OUT|Originate|EXECUTE.*bridge|Hangup sofia/internal' /var/log/freeswitch/freeswitch.log | tail -60\""))

print("==== webrtc_local + skykin_local ====")
print(run("docker exec skykin-freeswitch sh -c 'echo ===== webrtc =====; cat /etc/freeswitch/dialplan/default/00_webrtc_local.xml; echo ===== skykin =====; cat /etc/freeswitch/dialplan/default/00_skykin.xml'"))

c.close()
