from pathlib import Path
import re

# 1) Stop vanilla 80xx demo from stealing the queue
dp = Path("/root/skykin-fs-etc/dialplan/default.xml")
t = dp.read_text()
# Comment out del-group and add-group extensions (they match 80xx).
for name in ("del-group", "add-group"):
    pat = re.compile(
        rf'(<extension name="{name}">.*?</extension>)',
        re.S,
    )
    t2, n = pat.subn(lambda m: "<!-- skykin disabled\n" + m.group(1) + "\n-->", t, count=1)
    if n != 1:
        raise SystemExit(f"could not disable {name}")
    t = t2
dp.write_text(t)
print("disabled del-group/add-group")

# 2) Inbound DID: queue here, do not transfer to 8000
did = Path("/root/skykin-fs-etc/dialplan/public/01_skykin_did.xml")
did.write_text("""<include>
  <extension name="skykin_inbound_did">
    <condition field="destination_number" expression="^\\+?(?:251)?0?11113875[59]$">
      <action application="set" data="rtcp_audio_interval_msec=5000"/>
      <action application="set" data="rtp_advertise_ip=10.0.0.93"/>
      <action application="set" data="include_external_ip=false"/>
      <action application="set" data="rtp_secure_media=false"/>
      <action application="set" data="media_webrtc=false"/>
      <action application="set" data="domain_name=client1.skykin.local"/>
      <action application="export" data="domain_name=client1.skykin.local"/>
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="set" data="record_stereo=true"/>
      <action application="set" data="record_path=/var/lib/freeswitch/recordings/client1.skykin.local/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
      <action application="set" data="record_name=${uuid}.wav"/>
      <action application="answer"/>
      <action application="record_session" data="${record_path}/${record_name}"/>
      <action application="callcenter" data="8000@client1.skykin.local"/>
    </condition>
  </extension>
</include>
""")
print("rewrote inbound DID -> callcenter")

# 3) Fix empty bleg uuid: create_uuid() is the API form
sky = Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml")
s = sky.read_text()
s = s.replace("${create_uuid}", "${create_uuid()}")
# Remove the mistaken bleg_uuid on local A2A bridge
s = s.replace(
    '      <action application="set" data="bleg_uuid=${create_uuid()}"/>\n      <action application="bridge" data="{rtp_secure_media=optional,}',
    '      <action application="bridge" data="{rtp_secure_media=optional,}',
)
sky.write_text(s)
print("create_uuid() outbound", s.count("${create_uuid()}"), "bleg sets", s.count("bleg_uuid=${create_uuid()}"))
