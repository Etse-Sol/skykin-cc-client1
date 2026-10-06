from pathlib import Path

p = Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml")
t = p.read_text()

old_bridge = (
    '{absolute_codec_string=^^:PCMA:PCMU,'
    'rtcp_audio_interval_msec=0,'
    'rtcp_mux=false,'
    'rtp_secure_media=false,'
    'media_webrtc=false,'
    'api_on_answer=sched_api +1 none uuid_media_reneg ${uuid},'
    'rtp_advertise_ip=10.0.0.93,'
    'include_external_ip=false,'
    'ignore_early_media=false,'
    'sip_session_expires=180,'
    'sip_force_session_timer=true,'
    'origination_caller_id_number=+251111138755,'
    'origination_caller_id_name=+251111138755}'
)
new_bridge = (
    '{origination_uuid=${bleg_uuid},'
    'absolute_codec_string=^^:PCMA:PCMU,'
    'rtcp_audio_interval_msec=5000,'
    'rtcp_mux=false,'
    'rtp_secure_media=false,'
    'media_webrtc=false,'
    'api_on_answer=sched_api +1 none uuid_media_reneg ${bleg_uuid},'
    'rtp_advertise_ip=10.0.0.93,'
    'include_external_ip=false,'
    'ignore_early_media=false,'
    'sip_session_expires=180,'
    'sip_force_session_timer=true,'
    'origination_caller_id_number=+251111138755,'
    'origination_caller_id_name=+251111138755}'
)
if old_bridge not in t:
    raise SystemExit("old bridge not found:\n" + t[t.find("{absolute_codec"):t.find("{absolute_codec")+320])

t = t.replace(old_bridge, new_bridge)
needle = '      <action application="record_session" data="${record_path}/${record_name}"/>\n      <action application="bridge"'
insert = (
    '      <action application="record_session" data="${record_path}/${record_name}"/>\n'
    '      <action application="set" data="bleg_uuid=${create_uuid}"/>\n'
    '      <action application="bridge"'
)
# only outbound extensions have record_session then bridge; queue/local also have record then other apps
if t.count(needle) < 3:
    raise SystemExit("expected 3 outbound record+bridge blocks, got %s" % t.count(needle))
t = t.replace(needle, insert)
p.write_text(t)
print("ok bridges", t.count("origination_uuid=${bleg_uuid}"), "sets", t.count("bleg_uuid=${create_uuid}"))
