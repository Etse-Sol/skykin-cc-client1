"""Restore agent directory, local dialplan, and Ethio trunk on the live server."""
import sys
import time
import xml.sax.saxutils as xml

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=90):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


def xml_esc(s):
    return xml.escape(s, {'"': "&quot;", "'": "&apos;"})


# Passwords stay on the server; never printed.
rows = run(
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -t -A -c "
    "\"SELECT domain_name || E'\\t' || extension || E'\\t' || password "
    "FROM v_extensions e JOIN v_domains d ON d.domain_uuid=e.domain_uuid "
    "WHERE d.domain_name='client1.skykin.local' "
    "AND e.extension IN ('100','101','102','103','104');\""
).strip().splitlines()
ext_pass = {}
for line in rows:
    parts = line.split("\t")
    if len(parts) == 3:
        ext_pass[parts[1]] = parts[2]

gw_pass = run(
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -t -A -c "
    "\"SELECT password FROM v_gateways WHERE gateway='SIP' LIMIT 1;\""
).strip()
if gw_pass.lower().startswith("password "):
    gw_pass = gw_pass[9:]

print(f"extensions to provision: {sorted(ext_pass)}")
print(f"gateway password length: {len(gw_pass)}")

# --- 1) directory users 103 + 104 (and refresh 100-102) ---
for ext, pw in ext_pass.items():
    body = f"""<include>
  <user id="{xml_esc(ext)}">
    <params>
      <param name="password" value="{xml_esc(pw)}"/>
      <param name="vm-password" value="{xml_esc(ext)}"/>
    </params>
    <variables>
      <variable name="toll_allow" value="domestic,international,local"/>
      <variable name="accountcode" value="{xml_esc(ext)}"/>
      <variable name="user_context" value="default"/>
      <variable name="effective_caller_id_name" value="Extension {xml_esc(ext)}"/>
      <variable name="effective_caller_id_number" value="{xml_esc(ext)}"/>
      <variable name="outbound_caller_id_name" value="Extension {xml_esc(ext)}"/>
      <variable name="outbound_caller_id_number" value="{xml_esc(ext)}"/>
      <variable name="callgroup" value="skykin"/>
    </variables>
  </user>
</include>
"""
    sftp = c.open_sftp()
    with sftp.file(f"/tmp/{ext}.xml", "w") as f:
        f.write(body)
    sftp.close()
    run(f"docker cp /tmp/{ext}.xml skykin-freeswitch:/etc/freeswitch/directory/default/{ext}.xml")
    print(f"  wrote directory {ext}.xml")

# --- 2) agent-to-agent: all 1xx via user/ (WSS or UDP), not WSS-only 101|102 ---
webrtc_local = """<include>
  <extension name="webrtc_local" continue="false">
    <condition field="destination_number" expression="^(1\\d{2})$">
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="set" data="call_timeout=30"/>
      <action application="set" data="rtp_secure_media=optional"/>
      <action application="set" data="rtp_advertise_ip=196.189.236.140"/>
      <action application="set" data="include_external_ip=true"/>
      <action application="bridge" data="{rtp_secure_media=optional}user/$1@client1.skykin.local"/>
    </condition>
  </extension>
</include>
"""
sftp = c.open_sftp()
with sftp.file("/tmp/webrtc_local.xml", "w") as f:
    f.write(webrtc_local)
sftp.close()
for dest in (
    "/etc/freeswitch/dialplan/default/00_webrtc_local.xml",
    "/etc/freeswitch/dialplan/default/00_aa_webrtc_local.xml",
    "/etc/freeswitch/dialplan/client1.skykin.local/00_webrtc_local.xml",
):
    run(f"docker cp /tmp/webrtc_local.xml skykin-freeswitch:{dest}")
    print(f"  wrote {dest}")

# Relax the skykin_local OPUS-only bridge so MicroSIP and browsers can talk.
run(
    r"""docker exec skykin-freeswitch sh -c '
for f in /etc/freeswitch/dialplan/default/00_skykin.xml \
         /etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml; do
  [ -f "$f" ] || continue
  sed -i "s#absolute_codec_string=OPUS}#}#g" "$f"
  sed -i "s#media_webrtc=true,rtp_secure_media=optional,#rtp_secure_media=optional,#g" "$f"
done
'"""
)
print("  relaxed skykin_local codec lock")

# --- 3) IMS gateway ---
sip_xml = f"""<include>
  <gateway name="SIP">
    <param name="username" value="+251111138755"/>
    <param name="auth-username" value="+251111138755@ims.ethiotelecom.com"/>
    <param name="password" value="{xml_esc(gw_pass)}"/>
    <param name="from-user" value="+251111138755"/>
    <param name="from-domain" value="ims.ethiotelecom.com"/>
    <param name="realm" value="ims.ethiotelecom.com"/>
    <param name="proxy" value="ims.ethiotelecom.com"/>
    <param name="register-proxy" value="10.208.233.134"/>
    <param name="outbound-proxy" value="10.208.233.134"/>
    <param name="register" value="true"/>
    <param name="expire-seconds" value="3600"/>
    <param name="retry-seconds" value="30"/>
    <param name="context" value="public"/>
    <param name="caller-id-in-from" value="true"/>
    <param name="extension-in-contact" value="true"/>
  </gateway>
</include>
"""
sftp = c.open_sftp()
with sftp.file("/tmp/SIP.xml", "w") as f:
    f.write(sip_xml)
sftp.close()
run("docker exec skykin-freeswitch mkdir -p /etc/freeswitch/sip_profiles/external")
run("docker cp /tmp/SIP.xml skykin-freeswitch:/etc/freeswitch/sip_profiles/external/SIP.xml")
print("  wrote SIP.xml")

run(
    "grep -q 'ims.ethiotelecom.com' /etc/hosts || "
    "echo '10.208.233.134 ims.ethiotelecom.com' >> /etc/hosts"
)
print("  hosts: ims.ethiotelecom.com -> 10.208.233.134")

run(
    r"""docker exec skykin-freeswitch sh -c '
f=/etc/freeswitch/sip_profiles/external.xml
if grep -q "enable-100rel" "$f"; then
  sed -i "s#<!--[[:space:]]*<param name=\"enable-100rel\"[^>]*/>[[:space:]]*-->#<param name=\"enable-100rel\" value=\"true\"/>#" "$f"
  sed -i "s#<param name=\"enable-100rel\" value=\"[^\"]*\"/>#<param name=\"enable-100rel\" value=\"true\"/>#" "$f"
else
  sed -i "s#</settings>#    <param name=\"enable-100rel\" value=\"true\"/>\\n  </settings>#" "$f"
fi
'"""
)
print("  enable-100rel=true")

# --- 4) outbound + inbound dialplan ---
outbound = r"""
  <extension name="skykin_outbound_et_zero">
    <condition field="destination_number" expression="^0(\d{9})$">
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="set" data="call_timeout=60"/>
      <action application="export" data="domain_name=client1.skykin.local"/>
      <action application="set" data="record_path=/var/lib/freeswitch/recordings/client1.skykin.local/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
      <action application="set" data="record_name=${uuid}.wav"/>
      <action application="set" data="rtp_advertise_ip=196.189.236.140"/>
      <action application="set" data="include_external_ip=true"/>
      <action application="answer"/>
      <action application="set" data="ringback=${us-ring}"/>
      <action application="set" data="instant_ringback=true"/>
      <action application="set" data="record_stereo=true"/>
      <action application="record_session" data="${record_path}/${record_name}"/>
      <action application="bridge" data="{absolute_codec_string=^^:PCMA:PCMU,rtcp_audio_interval_msec=5000,rtp_advertise_ip=10.0.0.93,include_external_ip=false,ignore_early_media=true,origination_caller_id_number=+251111138755,origination_caller_id_name=+251111138755}sofia/gateway/SIP/+251$1"/>
    </condition>
  </extension>

  <extension name="skykin_outbound_et_nozero">
    <condition field="destination_number" expression="^(9\d{8})$">
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="set" data="call_timeout=60"/>
      <action application="export" data="domain_name=client1.skykin.local"/>
      <action application="set" data="record_path=/var/lib/freeswitch/recordings/client1.skykin.local/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
      <action application="set" data="record_name=${uuid}.wav"/>
      <action application="set" data="rtp_advertise_ip=196.189.236.140"/>
      <action application="set" data="include_external_ip=true"/>
      <action application="answer"/>
      <action application="set" data="ringback=${us-ring}"/>
      <action application="set" data="instant_ringback=true"/>
      <action application="set" data="record_stereo=true"/>
      <action application="record_session" data="${record_path}/${record_name}"/>
      <action application="bridge" data="{absolute_codec_string=^^:PCMA:PCMU,rtcp_audio_interval_msec=5000,rtp_advertise_ip=10.0.0.93,include_external_ip=false,ignore_early_media=true,origination_caller_id_number=+251111138755,origination_caller_id_name=+251111138755}sofia/gateway/SIP/+251$1"/>
    </condition>
  </extension>

  <extension name="skykin_outbound_et_e164">
    <condition field="destination_number" expression="^\+?(251\d{9})$">
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="set" data="call_timeout=60"/>
      <action application="export" data="domain_name=client1.skykin.local"/>
      <action application="set" data="record_path=/var/lib/freeswitch/recordings/client1.skykin.local/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
      <action application="set" data="record_name=${uuid}.wav"/>
      <action application="set" data="rtp_advertise_ip=196.189.236.140"/>
      <action application="set" data="include_external_ip=true"/>
      <action application="answer"/>
      <action application="set" data="ringback=${us-ring}"/>
      <action application="set" data="instant_ringback=true"/>
      <action application="set" data="record_stereo=true"/>
      <action application="record_session" data="${record_path}/${record_name}"/>
      <action application="bridge" data="{absolute_codec_string=^^:PCMA:PCMU,rtcp_audio_interval_msec=5000,rtp_advertise_ip=10.0.0.93,include_external_ip=false,ignore_early_media=true,origination_caller_id_number=+251111138755,origination_caller_id_name=+251111138755}sofia/gateway/SIP/+$1"/>
    </condition>
  </extension>
"""
sftp = c.open_sftp()
with sftp.file("/tmp/outbound_snip.xml", "w") as f:
    f.write(outbound)
sftp.close()
run("docker cp skykin-freeswitch:/etc/freeswitch/dialplan/default/00_skykin.xml /tmp/00_skykin.xml")
sky = run("cat /tmp/00_skykin.xml")
if "skykin_outbound_et_zero" not in sky:
    if "</include>" in sky:
        sky = sky.replace("</include>", outbound + "\n</include>", 1)
        sftp = c.open_sftp()
        with sftp.file("/tmp/00_skykin.xml", "w") as f:
            f.write(sky)
        sftp.close()
        run("docker cp /tmp/00_skykin.xml skykin-freeswitch:/etc/freeswitch/dialplan/default/00_skykin.xml")
        print("  injected outbound into 00_skykin.xml")
    else:
        print("  00_skykin.xml has no </include>")
else:
    print("  outbound already in 00_skykin.xml")

did = """<include>
  <extension name="skykin_inbound_did">
    <condition field="destination_number" expression="^\\+?(?:251)?0?11113875[59]$">
      <action application="set" data="rtcp_audio_interval_msec=5000"/>
      <action application="set" data="domain_name=client1.skykin.local"/>
      <action application="export" data="domain_name=client1.skykin.local"/>
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="transfer" data="8000 XML default"/>
    </condition>
  </extension>
</include>
"""
sftp = c.open_sftp()
with sftp.file("/tmp/01_skykin_did.xml", "w") as f:
    f.write(did)
sftp.close()
run("docker exec skykin-freeswitch mkdir -p /etc/freeswitch/dialplan/public")
run("docker cp /tmp/01_skykin_did.xml skykin-freeswitch:/etc/freeswitch/dialplan/public/01_skykin_did.xml")
print("  wrote inbound DID")

# Persist 103/104 in server .env so a later entrypoint run keeps them.
run(
    r"""python3 - <<'PY'
from pathlib import Path
p = Path("/opt/call-center-deployement/call-center/.env")
t = p.read_text()
old = "FS_DIRECTORY_USERS=100:11112222,101:1234567890,102:0987654321"
new = old + ",103:22223333"
if "103:" not in t and old in t:
    t = t.replace(old, new)
    p.write_text(t)
    print("updated .env FS_DIRECTORY_USERS")
else:
    print("env directory users already include 103 or pattern mismatch")
PY"""
)

# --- 5) reload ---
print(run("docker exec skykin-freeswitch fs_cli -x 'reloadxml'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile external killgw SIP'"))
time.sleep(2)
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile external restart'"))
time.sleep(6)
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status gateway SIP'"))

print("==== directory now ====")
print(run("docker exec skykin-freeswitch sh -c 'ls /etc/freeswitch/directory/default/10[0-4].xml'"))

print("==== webrtc_local match ====")
print(run("docker exec skykin-freeswitch grep -n destination_number /etc/freeswitch/dialplan/default/00_webrtc_local.xml"))

print("==== user 103 lookup ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'user_exists id 103 client1.skykin.local'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'user_data 103@client1.skykin.local attr id'"))

c.close()
print("DONE")
