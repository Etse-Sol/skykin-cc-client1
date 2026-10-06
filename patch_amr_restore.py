from pathlib import Path
src = Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml.bak-oneway")
dst = Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml")
if not src.exists():
    raise SystemExit("backup missing")
t = src.read_text()
old = "absolute_codec_string=^^:PCMA:PCMU,rtcp_audio_interval_msec=5000,rtp_advertise_ip=10.0.0.93,include_external_ip=false,ignore_early_media=true,origination_caller_id_number="
new = (
    "absolute_codec_string=^^:AMR:PCMA:PCMU,"
    "rtcp_audio_interval_msec=5000,"
    "rtp_advertise_ip=10.0.0.93,"
    "include_external_ip=false,"
    "ignore_early_media=true,"
    "sip_session_expires=180,"
    "sip_force_session_timer=true,"
    "origination_caller_id_number="
)
if old not in t:
    raise SystemExit("bridge string not found in backup")
t = t.replace(old, new)
dst.write_text(t)
print("restored answer/ringback and offered AMR")
print("AMR bridges", t.count("AMR:PCMA:PCMU"))
print("answer count", t.count('application="answer"'))
