#!/bin/bash
# Client1 ONLY — force welcome/waiting audio + no early answer in dialplan.
# Does not touch ahununu DID or skykin_inbound.lua.
set -euo pipefail

PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env | cut -d= -f2-)
FS() { docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1"; }

OPENING=/var/lib/freeswitch/recordings/client1.skykin.local/opening-long.wav
MUSIC=/var/lib/freeswitch/recordings/client1.skykin.local/music.wav
WAITING=/var/lib/freeswitch/recordings/client1.skykin.local/waiting-2.wav
MOH="file_string://${WAITING}!{loops=-1}${MUSIC}"
RINGBACK="{loops=-1}${MUSIC}"
LIVE=/opt/skykin/fs-live
mkdir -p "$LIVE"

echo "==== files ===="
docker exec skykin-freeswitch ls -lah "$OPENING" "$MUSIC" "$WAITING"

echo "==== BEFORE (audio lines) ===="
docker exec skykin-freeswitch sh -c 'grep -nE "answer|pre_answer|playback|cc_moh|ringback|ahununu|music|opening|waiting|skykin_inbound" /etc/freeswitch/dialplan/public/01_skykin_did.xml'

docker cp skykin-freeswitch:/etc/freeswitch/dialplan/public/01_skykin_did.xml /tmp/01_skykin_did.xml
cp -a /tmp/01_skykin_did.xml "/tmp/01_skykin_did.xml.bak.force-$(date +%H%M%S)"

python3 << PY
from pathlib import Path
import re

p = Path("/tmp/01_skykin_did.xml")
text = p.read_text()

opening = "${OPENING}"
music = "${MUSIC}"
waiting = "${WAITING}"
moh = "${MOH}"
ringback = "${RINGBACK}"

# Hard replace any leftover ahununu-music paths
text = text.replace(
    "/var/lib/freeswitch/recordings/client1.skykin.local/ahununu-music.wav",
    music,
)
text = text.replace("ahununu-music.wav", "music.wav")

# Remove early answer / old welcome playback / old ringback / old moh lines
# (we rebuild a clean end condition)
text = re.sub(
    r'<action application="(?:set|export)" data="cc_moh_override=[^"]*"/>\s*',
    "",
    text,
)
text = re.sub(
    r'<action application="(?:set|export)" data="(?:ringback|transfer_ringback)=[^"]*"/>\s*',
    "",
    text,
)

# Insert waiting MOH + export vars near recording setup (before ring_ready block)
insert = (
    f'      <action application="export" data="cc_moh_override={moh}"/>\n'
    f'      <action application="export" data="ringback={ringback}"/>\n'
    f'      <action application="export" data="transfer_ringback={ringback}"/>\n'
)
if "cc_moh_override=" not in text:
    if '<action application="set" data="record_stereo=true"/>' in text:
        text = text.replace(
            '<action application="set" data="record_stereo=true"/>',
            insert + '      <action application="set" data="record_stereo=true"/>',
            1,
        )
    else:
        # fallback: before first ring_ready
        text = text.replace(
            '<action application="ring_ready"/>',
            insert + '      <action application="ring_ready"/>',
            1,
        )

# Ensure cc_export_vars carries moh + ringback
if "cc_export_vars=" in text:
    def fix_vars(m):
        parts = [x for x in m.group(1).split(",") if x]
        for v in ("cc_moh_override", "ringback", "transfer_ringback", "execute_on_hangup"):
            if v not in parts:
                # only add execute_on_hangup if hangup export exists in file
                if v == "execute_on_hangup" and "execute_on_hangup" not in text:
                    continue
                parts.append(v)
        # unique preserve order
        seen = set()
        out = []
        for x in parts:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return f'<action application="set" data="cc_export_vars={",".join(out)}"/>'
    text = re.sub(
        r'<action application="set" data="cc_export_vars=([^"]*)"/>',
        fix_vars,
        text,
        count=1,
    )

# Replace the FINAL condition (welcome + lua) with a known-good block.
# Must NOT use answer() here — counting should wait for agent.
new_cond = f'''    <condition>
      <action application="ring_ready"/>
      <action application="pre_answer"/>
      <action application="playback" data="{opening}"/>
      <action application="playback" data="{music}"/>
      <action application="lua" data="/etc/freeswitch/scripts/skykin_inbound.lua"/>
    </condition>'''

# Remove every trailing <condition>...</condition> that contains skykin_inbound.lua
text2, n = re.subn(
    r'\s*<condition>\s*'
    r'(?:<action[^>]*>\s*)*?'
    r'<action application="lua" data="/etc/freeswitch/scripts/skykin_inbound\.lua"/>\s*'
    r'</condition>',
    "\n" + new_cond,
    text,
    count=1,
    flags=re.S,
)
if n != 1:
    raise SystemExit("Could not replace skykin_inbound condition block")
text = text2

# Final safety: no answer() before lua in this file's welcome path
# (keep execute_on_answer=record_session — that does not answer by itself)
if re.search(r'<action application="answer"/>\s*\n\s*<action application="playback"', text):
    raise SystemExit("ERROR: answer+playback still present — abort")

if "ahununu-music" in text:
    raise SystemExit("ERROR: ahununu-music still in dialplan — abort")
if music not in text or opening not in text or "cc_moh_override=" not in text:
    raise SystemExit("ERROR: expected music/opening/moh missing — abort")

p.write_text(text)
print("FORCE PATCH OK")
print("--- audio-related lines ---")
for i, line in enumerate(text.splitlines(), 1):
    if any(k in line for k in (
        "ring_ready", "pre_answer", "answer", "playback", "cc_moh",
        "ringback", "skykin_inbound", "opening", "music", "waiting", "ahununu"
    )):
        print(f"{i}:{line}")
PY

docker cp /tmp/01_skykin_did.xml skykin-freeswitch:/etc/freeswitch/dialplan/public/01_skykin_did.xml
cp /tmp/01_skykin_did.xml "$LIVE/01_skykin_did.xml"

echo "==== AFTER ===="
docker exec skykin-freeswitch sh -c 'grep -nE "answer|pre_answer|playback|cc_moh|ringback|ahununu|music|opening|waiting|skykin_inbound" /etc/freeswitch/dialplan/public/01_skykin_did.xml'

FS "reloadxml"
echo DONE
echo
echo "Expected caller flow:"
echo "  1) opening-long"
echo "  2) music.wav once"
echo "  3) music loops while agent rings / until pickup"
echo "  4) if waiting list: waiting-2 then music loops until agent"
echo "  5) dialplan has pre_answer only (no answer before agent)"
echo
echo "If timer still starts during welcome on Ethio, the carrier may bill on 183 early media — FreeSWITCH cannot fully stop that."
