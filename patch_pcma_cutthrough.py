from pathlib import Path
p = Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml")
t = p.read_text()
old_br = (
    "absolute_codec_string=^^:AMR:PCMA:PCMU,"
    "rtcp_audio_interval_msec=5000,"
    "rtp_advertise_ip=10.0.0.93,"
    "include_external_ip=false,"
    "ignore_early_media=true,"
    "sip_session_expires=180,"
    "sip_force_session_timer=true,"
    "origination_caller_id_number="
)
new_br = (
    "absolute_codec_string=^^:PCMA:PCMU,"
    "rtcp_audio_interval_msec=0,"
    "rtp_advertise_ip=10.0.0.93,"
    "include_external_ip=false,"
    "ignore_early_media=false,"
    "sip_session_expires=180,"
    "sip_force_session_timer=true,"
    "origination_caller_id_number="
)
if old_br not in t:
    raise SystemExit("bridge string not found:\n" + t[t.find("absolute_codec"):t.find("absolute_codec")+200])
t = t.replace(old_br, new_br)
old_rb = (
    '      <action application="set" data="ringback=${us-ring}"/>\n'
    '      <action application="set" data="instant_ringback=true"/>\n'
)
t = t.replace(old_rb, "")
p.write_text(t)
print("pcma_bridges", t.count("PCMA:PCMU"))
print("amr_left", t.count("AMR:"))
print("ignore_false", t.count("ignore_early_media=false"))
print("ringback_left", t.count("ringback"))
