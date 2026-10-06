#!/bin/bash
# Fix silent inbound/outbound WAVs: use uuid_record on answer, mono, not pre_answer.
set -eu

COMMIT="${SKYKIN_RESTORE_COMMIT:-HEAD}"
APP="${SKYKIN_APP:-/opt/skykin/app}"
PW=$(grep -E '^ESL_PASSWORD=' "$APP/.env" | cut -d= -f2-)
FS() { docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1"; }

echo "=== 1) Deploy skykin_inbound.lua (uuid_record on answer) ==="
if [ -f "$APP/docker/freeswitch/scripts/skykin_inbound.lua" ]; then
  docker cp "$APP/docker/freeswitch/scripts/skykin_inbound.lua" \
    skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
else
  echo "  copy skykin_inbound.lua to $APP/docker/freeswitch/scripts/ first"
  exit 1
fi

echo "=== 2) Inbound dialplan — remove execute_on_answer (lua handles it) ==="
docker cp skykin-freeswitch:/etc/freeswitch/dialplan/public/02_skykin_did_ahununu.xml /tmp/02_in.xml
python3 <<'PY'
from pathlib import Path
t = Path("/tmp/02_in.xml").read_text()
for line in [
    '      <action application="set" data="record_stereo=true"/>\n',
    '      <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>\n',
    '      <action application="set" data="record_name=${uuid}.wav"/>\n',
    '      <action application="set" data="execute_on_answer=record_session ${record_path}/${record_name}"/>\n',
]:
    t = t.replace(line, "")
Path("/tmp/02_in.xml").write_text(t)
print("inbound dialplan cleaned")
PY
docker cp /tmp/02_in.xml skykin-freeswitch:/etc/freeswitch/dialplan/public/02_skykin_did_ahununu.xml

echo "=== 3) Outbound — record on answer, not pre_answer ==="
docker cp skykin-freeswitch:/etc/freeswitch/dialplan/01_skykin_ahununu.xml /tmp/01_out.xml
python3 <<'PY'
from pathlib import Path
p = Path("/tmp/01_out.xml")
t = p.read_text()
old = """        <action application="pre_answer"/>
        <action application="export" data="domain_name=ahununu"/>
        <action application="set" data="record_stereo=true"/>
        <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/\${strftime(%d)}"/>
        <action application="set" data="record_name=\${uuid}.wav"/>
        <action application="record_session" data="\${record_path}/\${record_name}"/>
        <action application="set" data="bleg_uuid=\${create_uuid()}"/>"""
new = """        <action application="pre_answer"/>
        <action application="export" data="domain_name=ahununu"/>
        <action application="set" data="record_stereo=false"/>
        <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/\${strftime(%d)}"/>
        <action application="set" data="record_name=\${uuid}.wav"/>
        <action application="set" data="execute_on_answer=record_session \${record_path}/\${record_name}"/>
        <action application="set" data="bleg_uuid=\${create_uuid()}"/>"""
# Fix escaped braces in file - read actual file
t2 = p.read_text()
old2 = """        <action application="pre_answer"/>
        <action application="export" data="domain_name=ahununu"/>
        <action application="set" data="record_stereo=true"/>
        <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
        <action application="set" data="record_name=${uuid}.wav"/>
        <action application="record_session" data="${record_path}/${record_name}"/>
        <action application="set" data="bleg_uuid=${create_uuid()}"/>"""
new2 = """        <action application="pre_answer"/>
        <action application="export" data="domain_name=ahununu"/>
        <action application="set" data="record_stereo=false"/>
        <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
        <action application="set" data="record_name=${uuid}.wav"/>
        <action application="set" data="execute_on_answer=record_session ${record_path}/${record_name}"/>
        <action application="set" data="bleg_uuid=${create_uuid()}"/>"""
if old2 not in t2:
    raise SystemExit("outbound pattern not found")
p.write_text(t2.replace(old2, new2))
print("outbound patched", t2.count(old2), "routes")
PY
docker cp /tmp/01_out.xml skykin-freeswitch:/etc/freeswitch/dialplan/01_skykin_ahununu.xml

mkdir -p /opt/skykin/fs-live
cp -a /tmp/02_in.xml /opt/skykin/fs-live/02_skykin_did_ahununu.xml
cp -a /tmp/01_out.xml /opt/skykin/fs-live/01_skykin_ahununu.xml
FS "reloadxml"

echo "DONE — place one inbound + one outbound test call, then re-run Python peak check on new .wav"
