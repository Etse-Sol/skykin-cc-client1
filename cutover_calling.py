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


print("==== nginx -> gateway ====")
print(run(r"""
docker exec skykin-web sh -c '
f=/etc/nginx/sites-enabled/skykin.conf
sed -i "s#proxy_pass https://172.22.0.1:7443;#proxy_pass http://172.22.0.1:18081;#" "$f"
grep -n proxy_pass "$f"
nginx -t && nginx -s reload
'
ufw allow from 172.16.0.0/12 to any port 18081 proto tcp comment skykin-ws-sip >/dev/null
"""))

print("==== restore webrtc_local to user/ ====")
print(run(r"""
docker exec skykin-freeswitch sh -c '
for f in /etc/freeswitch/dialplan/default/00_webrtc_local.xml \
         /etc/freeswitch/dialplan/default/00_aa_webrtc_local.xml \
         /etc/freeswitch/dialplan/client1.skykin.local/00_webrtc_local.xml; do
  [ -f "$f" ] || continue
  cat > "$f" << "XML"
<include>
  <extension name="webrtc_local" continue="false">
    <condition field="destination_number" expression="^(1\d{2})$">
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="set" data="call_timeout=30"/>
      <action application="set" data="rtp_secure_media=optional"/>
      <action application="set" data="media_webrtc=true"/>
      <action application="set" data="rtp_advertise_ip=196.189.236.140"/>
      <action application="set" data="include_external_ip=true"/>
      <action application="bridge" data="{media_webrtc=true,rtp_secure_media=optional,rtp_advertise_ip=196.189.236.140,include_external_ip=true}user/$1@client1.skykin.local"/>
    </condition>
  </extension>
</include>
XML
done
'
docker exec skykin-freeswitch fs_cli -x 'reloadxml'
"""))

print("==== outbound still present ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -n skykin_outbound /etc/freeswitch/dialplan/default/00_skykin.xml\""))
print("==== trunk ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status gateway SIP' | grep -E 'State|Status|Name'"))
c.close()
