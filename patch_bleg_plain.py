from pathlib import Path

p = Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml")
t = p.read_text()
old = (
    "absolute_codec_string=^^:PCMA:PCMU,"
    "rtcp_audio_interval_msec=0,"
    "rtp_advertise_ip=10.0.0.93,"
    "include_external_ip=false,"
    "ignore_early_media=false,"
    "sip_session_expires=180,"
    "sip_force_session_timer=true,"
    "origination_caller_id_number="
)
new = (
    "absolute_codec_string=^^:PCMA:PCMU,"
    "rtcp_audio_interval_msec=0,"
    "rtcp_mux=false,"
    "rtp_secure_media=false,"
    "media_webrtc=false,"
    "rtp_advertise_ip=10.0.0.93,"
    "include_external_ip=false,"
    "ignore_early_media=false,"
    "sip_session_expires=180,"
    "sip_force_session_timer=true,"
    "origination_caller_id_number="
)
if old not in t:
    raise SystemExit("bridge string not found:\n" + t[t.find("absolute_codec"):t.find("absolute_codec")+220])
p.write_text(t.replace(old, new))
print("bridges_updated", t.replace(old, new).count("rtcp_mux=false"))

leftover = Path("/root/skykin-fs-etc/dialplan/client1.skykin.local/00_ethio_mobile.xml")
if leftover.exists():
    leftover.rename(leftover.with_name("00_ethio_mobile.xml.noload"))
    print("noloaded leftover ethio_mobile")
else:
    print("leftover already gone")
