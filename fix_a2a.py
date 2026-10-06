import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


sftp = c.open_sftp()

# Fast-fail directory handler so INVITE auth does not hang (FusionPBX scripts
# are not mounted in this container).
stub = r'''-- SkyKin stub: FusionPBX xml_handler is not mounted. Return "not found"
-- immediately so FreeSWITCH falls back to the static directory XML.
XML_STRING = [[<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<document type="freeswitch/xml">
  <section name="result">
    <result status="not found"/>
  </section>
</document>]]
'''
with sftp.file("/tmp/app.lua", "w") as f:
    f.write(stub)

dest = r'''local api = freeswitch.API()
local user = argv[1] or ""
local domain = argv[2] or "client1.skykin.local"
local contact = api:execute("sofia_contact", "*/" .. user .. "@" .. domain) or ""
if contact == "" or contact:find("error") or contact:find("not found") then
  stream:write("error/user_not_registered")
  return
end
local vars = "rtp_secure_media=optional,rtp_advertise_ip=196.189.236.140,include_external_ip=true"
if contact:find("transport=ws") then
  vars = vars .. ",media_webrtc=true"
end
stream:write("{" .. vars .. "}" .. contact)
'''
with sftp.file("/tmp/skykin_dest.lua", "w") as f:
    f.write(dest)

webrtc = r'''<include>
  <extension name="webrtc_local" continue="false">
    <condition field="destination_number" expression="^(1\d{2})$">
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="set" data="call_timeout=30"/>
      <action application="set" data="rtp_secure_media=optional"/>
      <action application="set" data="rtp_advertise_ip=196.189.236.140"/>
      <action application="set" data="include_external_ip=true"/>
      <action application="bridge" data="${lua(skykin_dest.lua $1 client1.skykin.local)}"/>
    </condition>
  </extension>
</include>
'''
with sftp.file("/tmp/webrtc_local.xml", "w") as f:
    f.write(webrtc)
sftp.close()

print(run("docker cp /tmp/app.lua skykin-freeswitch:/usr/share/freeswitch/scripts/app.lua"))
print(run("docker cp /tmp/skykin_dest.lua skykin-freeswitch:/usr/share/freeswitch/scripts/skykin_dest.lua"))
for dest_path in (
    "/etc/freeswitch/dialplan/default/00_webrtc_local.xml",
    "/etc/freeswitch/dialplan/default/00_aa_webrtc_local.xml",
    "/etc/freeswitch/dialplan/client1.skykin.local/00_webrtc_local.xml",
):
    print(run(f"docker cp /tmp/webrtc_local.xml skykin-freeswitch:{dest_path}"))

# Stop nginx from buffering large WebRTC INVITE frames.
print(run(r"""docker exec skykin-web sh -c '
f=/etc/nginx/sites-enabled/skykin.conf
if ! grep -q proxy_buffering "$f"; then
  sed -i "/proxy_http_version 1.1;/a\\        proxy_buffering off;\\n        proxy_request_buffering off;" "$f"
  cp "$f" /etc/nginx/sites-available/skykin.conf
fi
nginx -t && nginx -s reload
grep -n "proxy_buffering\\|proxy_pass" /etc/nginx/sites-enabled/skykin.conf
'"""))

print(run("docker exec skykin-freeswitch fs_cli -x 'reloadxml'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'lua skykin_dest.lua 102 client1.skykin.local'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'lua skykin_dest.lua 101 client1.skykin.local'"))
print("DONE")
c.close()
