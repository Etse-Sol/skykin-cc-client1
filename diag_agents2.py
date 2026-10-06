import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=45):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== directory users on disk ====")
print(run("docker exec skykin-freeswitch sh -c 'ls -l /etc/freeswitch/directory/default/; echo ---; ls /usr/share/freeswitch/scripts/app/xml_handler 2>&1 | head'"))

print("==== webrtc_local + wss_contact ====")
print(run("docker exec skykin-freeswitch sh -c 'grep -rn webrtc_local /etc/freeswitch/dialplan 2>/dev/null; echo ===== FILE =====; find /etc/freeswitch /usr/share/freeswitch -name \"*webrtc*\" -o -name \"wss_contact*\" 2>/dev/null'"))

print("==== lua.conf full ====")
print(run("docker exec skykin-freeswitch cat /etc/freeswitch/autoload_configs/lua.conf.xml"))

print("==== compose env on host ====")
print(run("ls -l /opt/call-center-deployement /opt/call-center* /opt/skykin* 2>/dev/null; echo ---; find /opt -name 'docker-compose.yml' -o -name '.env' 2>/dev/null | head -40"))

print("==== FS env inside container ====")
print(run("docker inspect skykin-freeswitch --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E 'FS_|FUSION|EXTERNAL|CDR|ESL'"))

print("==== mounts ====")
print(run("docker inspect skykin-freeswitch --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'"))

print("==== 103/104 full row (no password print: lengths + context + uuid) ====")
print(run("""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT e.extension, e.enabled, e.user_context, d.domain_name,
       length(e.password) AS pw_len, e.extension_uuid
FROM v_extensions e
JOIN v_domains d ON d.domain_uuid = e.domain_uuid
WHERE e.extension IN ('103','104','101','102');" """))

print("==== extension 103 password for directory (needed to provision) ====")
print(run("""docker exec skykin-db psql -U fusionpbx -d fusionpbx -t -A -c "
SELECT domain_name || '|' || extension || '|' || password
FROM v_extensions e
JOIN v_domains d ON d.domain_uuid = e.domain_uuid
WHERE e.extension IN ('100','101','102','103','104')
ORDER BY domain_name, extension;" """))

print("==== gateway DB ====")
print(run("""docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT gateway, username, proxy, register, enabled, from_user, from_domain, realm
FROM v_gateways;" """))

print("==== enable-100rel / ext-rtp ====")
print(run("docker exec skykin-freeswitch sh -c 'grep -n \"enable-100rel\\|ext-rtp-ip\\|ext-sip-ip\\|local-network\" /etc/freeswitch/sip_profiles/external.xml /etc/freeswitch/sip_profiles/internal.xml'"))

print("==== webrtc_local xml ====")
print(run("docker exec skykin-freeswitch sh -c 'grep -rl webrtc_local /etc/freeswitch | while read f; do echo ===== $f =====; cat \"$f\"; done'"))

c.close()
