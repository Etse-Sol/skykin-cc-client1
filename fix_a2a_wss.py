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


dest = (
    'local api = freeswitch.API()\n'
    'local user = argv[1] or ""\n'
    'local domain = argv[2] or "client1.skykin.local"\n'
    'local contact = api:execute("sofia_contact", "*/" .. user .. "@" .. domain) or ""\n'
    'if contact == "" or contact:find("error") or contact:find("not found") then\n'
    '  stream:write("error/user_not_registered")\n'
    '  return\n'
    'end\n'
    'if contact:find("transport=ws") or contact:find(".invalid") then\n'
    '  stream:write("{media_webrtc=true,rtp_secure_media=optional,rtp_advertise_ip=196.189.236.140,include_external_ip=true}sofia/internal/" .. user .. "@" .. domain)\n'
    'else\n'
    '  stream:write("{rtp_secure_media=optional}" .. contact)\n'
    'end\n'
)
sftp = c.open_sftp()
with sftp.file("/tmp/skykin_dest.lua", "w") as f:
    f.write(dest)
sftp.close()
print(run("docker cp /tmp/skykin_dest.lua skykin-freeswitch:/usr/share/freeswitch/scripts/skykin_dest.lua"))

print("==== pin internal ext-rtp to public IP ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'sed -i \"s#name=\\\"ext-rtp-ip\\\" value=\\\"[^\\\"]*\\\"#name=\\\"ext-rtp-ip\\\" value=\\\"196.189.236.140\\\"#\" "
    "/etc/freeswitch/sip_profiles/internal.xml; "
    "sed -i \"s#name=\\\"ext-sip-ip\\\" value=\\\"[^\\\"]*\\\"#name=\\\"ext-sip-ip\\\" value=\\\"196.189.236.140\\\"#\" "
    "/etc/freeswitch/sip_profiles/internal.xml; "
    "grep -n \"ext-rtp-ip\\|ext-sip-ip\\|local-network-acl\" /etc/freeswitch/sip_profiles/internal.xml'"
))

print("==== patch dashboard contactParams ====")
print(run(
    "docker exec skykin-web sh -c "
    "\"grep -n contactParams /var/www/fusionpbx/app/agent_dashboard/index.php || "
    "sed -i \\\"s/authorizationPassword: pass,/authorizationPassword: pass,\\\\n        contactParams: { transport: 'wss' },/\\\" "
    "/var/www/fusionpbx/app/agent_dashboard/index.php; "
    "grep -n contactParams /var/www/fusionpbx/app/agent_dashboard/index.php\""
))

print(run("docker exec skykin-freeswitch fs_cli -x 'reloadxml'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal restart'"))
print(run("sleep 2; docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg' | grep -E 'User:|Agent:|Status:|Total'"))
print("DONE")
c.close()
