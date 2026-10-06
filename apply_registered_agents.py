"""Enable outbound + queue for every SIP-registered agent."""
from pathlib import Path
import re
import subprocess

OUT_RE = re.compile(
    r'(<extension name="skykin_outbound_et_(?:zero|nozero|e164)">.*?</extension>)',
    re.S,
)

default_dp = Path("/root/skykin-fs-etc/dialplan/default/00_skykin.xml").read_text()
blocks = OUT_RE.findall(default_dp)
if len(blocks) != 3:
    raise SystemExit(f"expected 3 outbound extensions, got {len(blocks)}")

domain_path = Path("/root/skykin-fs-etc/dialplan/01_skykin_client1.skykin.local.xml")
dom = domain_path.read_text()
dom = OUT_RE.sub("", dom)
if "</context>" not in dom:
    raise SystemExit("domain context missing")
insert = "\n".join(blocks) + "\n"
dom = dom.replace("</context>", insert + "  </context>", 1)
domain_path.write_text(dom)
print("domain outbound copied")

# Registered extensions from sofia
reg = subprocess.check_output(
    ["docker", "exec", "skykin-freeswitch", "fs_cli", "-x",
     "sofia status profile internal reg"],
    text=True,
)
exts = sorted(set(re.findall(r"User:\s+(\d+)@client1\.skykin\.local", reg)))
print("registered", exts)

agents = {
    "101": "64c5f323-cd40-48ef-a97f-22d546be8b57",
    "102": "031ab55a-74f4-4c4a-9252-faaa4a1f4e5e",
    "103": "cd794b4f-f54e-4110-ba5d-537a034c243c",
    "104": "b3867d46-795b-47bd-a933-d90d16f10a75",
}
webrtc = (
    "[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,"
    "rtp_advertise_ip=196.189.236.140,include_external_ip=true]"
)
# MicroSIP is plain RTP — WebRTC SDP would make inbound fail.
plain = "[leg_timeout=30,rtp_secure_media=false,media_webrtc=false]"

def fs(cmd):
    print(subprocess.check_output(
        ["docker", "exec", "skykin-freeswitch", "fs_cli", "-x", cmd],
        text=True,
    ).strip())

fs("reloadxml")
for ext in exts:
    uid = agents.get(ext)
    if not uid:
        print("skip unknown ext", ext)
        continue
    contact = (plain if ext == "101" else webrtc) + f"user/{ext}@client1.skykin.local"
    fs(f"callcenter_config agent set contact {uid} '{contact}'")
    fs(f"callcenter_config agent set status {uid} Available")
    fs(f"callcenter_config agent set state {uid} Waiting")
    fs(f"callcenter_config agent set max_no_answer {uid} 999")
    fs(f"callcenter_config tier add 8000@client1.skykin.local {uid} 1 1")

print("==== agents ====")
print(subprocess.check_output(
    ["docker", "exec", "skykin-freeswitch", "fs_cli", "-x",
     "callcenter_config agent list"],
    text=True,
))
