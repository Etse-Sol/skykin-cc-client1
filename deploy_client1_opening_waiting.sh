#!/bin/bash
# Client1 ONLY — welcome + waiting audio (ecs-cc).
# Does NOT touch ahununu dialplan, ahununu recordings, or skykin_inbound.lua.
# Does NOT change callcenter.conf moh-sound (empty on purpose for Ethio bridge).
set -euo pipefail

PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env | cut -d= -f2-)
FS() { docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1"; }

REC=/var/lib/freeswitch/recordings/client1.skykin.local
LIVE=/opt/skykin/fs-live
mkdir -p "$LIVE"

echo "==== 0) Find uploaded WAVs in client1 domain ===="
docker exec skykin-freeswitch sh -c "ls -lah '$REC' | egrep -i 'opening|waiting|music|ahununu' || ls -lah '$REC'"

find_one() {
  # $1 = find expression pieces, print first match inside container
  docker exec skykin-freeswitch sh -c "find '$REC' -maxdepth 2 -type f \( $1 \) 2>/dev/null | head -1"
}

OPENING=$(find_one "-iname '*opening*long*' -o -iname 'opening-long.wav' -o -iname 'opening_long.wav'")
MUSIC=$(find_one "-iname '*ahununu*music*' -o -iname '*ahununu*mus*' -o -iname 'ahununu-music.wav' -o -iname 'ahununu_music.wav'")
WAITING=$(find_one "-iname 'waiting-2.wav' -o -iname '*waiting*2*'")

if [ -z "$OPENING" ]; then
  echo "ERROR: opening-long WAV not found under $REC"
  echo "Upload/rename it in FusionPBX client1 recordings, then re-run."
  exit 1
fi
if [ -z "$MUSIC" ]; then
  echo "ERROR: ahununu music WAV not found under $REC"
  exit 1
fi
if [ -z "$WAITING" ]; then
  echo "ERROR: waiting-2 WAV not found under $REC"
  exit 1
fi

echo "OPENING=$OPENING"
echo "MUSIC=$MUSIC"
echo "WAITING=$WAITING"

# MOH while in queue: play waiting once, then loop music (call already answered by welcome).
MOH="file_string://${WAITING}!{loops=-1}${MUSIC}"

echo "==== 1) Backup client1 DID only ===="
docker cp skykin-freeswitch:/etc/freeswitch/dialplan/public/01_skykin_did.xml /tmp/01_skykin_did.xml
cp -a /tmp/01_skykin_did.xml "/tmp/01_skykin_did.xml.bak.$(date +%Y%m%d%H%M%S)"
# Safety: refuse if this file looks like ahununu
if grep -q 'ahununu\|11619803' /tmp/01_skykin_did.xml; then
  echo "ERROR: 01_skykin_did.xml unexpectedly mentions ahununu — aborting"
  exit 1
fi

echo "==== 2) Patch welcome + waiting override (python) ===="
python3 << PY
from pathlib import Path
import re

p = Path("/tmp/01_skykin_did.xml")
text = p.read_text()

opening = "${OPENING}"
music = "${MUSIC}"
moh = "${MOH}"

# --- welcome: ring_ready -> answer -> opening-long -> music -> lua ---
# Replace any existing opening-2 / opening-long playback block after ring_ready.
cond_pat = re.compile(
    r'(<condition>\s*'
    r'<action application="ring_ready"/>\s*)'
    r'(?:<action application="answer"/>\s*)?'
    r'(?:<action application="playback" data="[^"]*"/>\s*)*'
    r'(<action application="lua" data="/etc/freeswitch/scripts/skykin_inbound.lua"/>\s*'
    r'</condition>)',
    re.S,
)

def welcome_repl(m):
    return (
        m.group(1)
        + '      <action application="answer"/>\n'
        + f'      <action application="playback" data="{opening}"/>\n'
        + f'      <action application="playback" data="{music}"/>\n'
        + m.group(2)
    )

text2, n = cond_pat.subn(welcome_repl, text, count=1)
if n != 1:
    raise SystemExit("Could not find client1 ring_ready/lua condition to patch welcome")
text = text2

# --- waiting: export cc_moh_override (do not leave it empty) ---
# Replace empty or previous override.
if re.search(r'cc_moh_override=', text):
    text = re.sub(
        r'<action application="(?:set|export)" data="cc_moh_override=[^"]*"/>\s*',
        "",
        text,
    )
# Insert export just before record_stereo or after originate_early_media if present
insert = (
    f'      <action application="export" data="cc_moh_override={moh}"/>\n'
)
if 'cc_moh_override=' not in text:
    if '<action application="set" data="record_stereo=true"/>' in text:
        text = text.replace(
            '<action application="set" data="record_stereo=true"/>',
            insert + '      <action application="set" data="record_stereo=true"/>',
            1,
        )
    else:
        text = text.replace(
            '<action application="ring_ready"/>',
            insert + '      <action application="ring_ready"/>',
            1,
        )

# Ensure cc_export_vars includes cc_moh_override so callcenter inherits it
if 'cc_export_vars=' in text:
    def fix_export_vars(m):
        raw = m.group(1)
        parts = [x for x in raw.split(",") if x]
        if "cc_moh_override" not in parts:
            parts.append("cc_moh_override")
        if "execute_on_hangup" not in parts and "execute_on_hangup" in text:
            # keep existing hangup export if present elsewhere
            pass
        return f'<action application="set" data="cc_export_vars={",".join(parts)}"/>'

    text = re.sub(
        r'<action application="set" data="cc_export_vars=([^"]*)"/>',
        fix_export_vars,
        text,
        count=1,
    )
else:
    text = text.replace(
        insert,
        insert + '      <action application="set" data="cc_export_vars=cc_moh_override,execute_on_hangup"/>\n',
        1,
    )

p.write_text(text)
print("Patched OK")
print("--- welcome / moh snippet ---")
for i, line in enumerate(text.splitlines(), 1):
    if any(k in line for k in ("ring_ready", "answer", "playback", "cc_moh", "cc_export", "skykin_inbound")):
        print(f"{i}:{line}")
PY

echo "==== 3) Install + persist (client1 file only) ===="
docker cp /tmp/01_skykin_did.xml skykin-freeswitch:/etc/freeswitch/dialplan/public/01_skykin_did.xml
cp /tmp/01_skykin_did.xml "$LIVE/01_skykin_did.xml"

echo "==== 4) Confirm ahununu untouched ===="
docker exec skykin-freeswitch sh -c 'ls /etc/freeswitch/dialplan/public/02_skykin_did_ahununu.xml 2>/dev/null && echo ahununu_did_present || echo ahununu_did_absent'
docker exec skykin-freeswitch sh -c 'grep -nE "opening|waiting|cc_moh|playback" /etc/freeswitch/dialplan/public/02_skykin_did_ahununu.xml 2>/dev/null | head -5 || true'

echo "==== 5) reloadxml (no mod_callcenter reload) ===="
FS "reloadxml"

echo "==== DONE ===="
echo "Flow (client1 755/756):"
echo "  1) opening-long"
echo "  2) ahununu music"
echo "  3) ring agent (unchanged lua)"
echo "  4) if waiting list: waiting-2 once, then loop ahununu music"
echo "Test with one Ready agent (welcome+music then connect) and one busy (waiting audio)."
