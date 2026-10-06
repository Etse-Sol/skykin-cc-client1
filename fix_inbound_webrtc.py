from pathlib import Path

did = Path("/root/skykin-fs-etc/dialplan/public/01_skykin_did.xml")
did.write_text("""<include>
  <extension name="skykin_inbound_did">
    <condition field="destination_number" expression="^\\+?(?:251)?0?11113875[59]$">
      <action application="set" data="rtcp_audio_interval_msec=0"/>
      <action application="set" data="send_silence_when_idle=100"/>
      <action application="set" data="rtp_advertise_ip=10.0.0.93"/>
      <action application="set" data="include_external_ip=false"/>
      <action application="set" data="rtp_secure_media=false"/>
      <action application="set" data="media_webrtc=false"/>
      <action application="set" data="domain_name=client1.skykin.local"/>
      <action application="export" data="domain_name=client1.skykin.local"/>
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="set" data="cc_moh_override="/>
      <action application="set" data="record_stereo=true"/>
      <action application="set" data="record_path=/var/lib/freeswitch/recordings/client1.skykin.local/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
      <action application="set" data="record_name=${uuid}.wav"/>
      <action application="set" data="execute_on_answer=record_session ${record_path}/${record_name}"/>
      <action application="callcenter" data="8000@client1.skykin.local"/>
    </condition>
  </extension>
</include>
""")
print("did written: no early answer, no opus export")
