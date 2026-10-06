from pathlib import Path
p = Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml")
t = p.read_text()
old = "rtcp_mux=false,rtp_secure_media=false,media_webrtc=false,"
new = (
    "rtcp_mux=false,rtp_secure_media=false,media_webrtc=false,"
    "api_on_answer=sched_api +1 none uuid_media_reneg ${uuid},"
)
if old not in t:
    raise SystemExit("lock vars not found:\n" + t[t.find("absolute_codec"):t.find("absolute_codec")+280])
if "uuid_media_reneg" in t:
    print("reinvite already present")
else:
    p.write_text(t.replace(old, new))
    print("reinvite added", p.read_text().count("uuid_media_reneg"))
