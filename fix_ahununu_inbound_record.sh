#!/bin/bash
# Enable inbound recording on ahununu (records when agent answers).
set -eu

FILE=/etc/freeswitch/dialplan/public/02_skykin_did_ahununu.xml
docker cp skykin-freeswitch:"$FILE" /tmp/02_skykin_did_ahununu.xml
cp -a /tmp/02_skykin_did_ahununu.xml /tmp/02_skykin_did_ahununu.xml.bak

python3 <<'PY'
from pathlib import Path
p = Path("/tmp/02_skykin_did_ahununu.xml")
t = p.read_text()
if "execute_on_answer=record_session" in t:
    print("already has inbound recording")
    raise SystemExit(0)
needle = """      <action application="set" data="originate_early_media=false"/>
      <action application="set" data="instant_ringback=true"/>"""
insert = """      <action application="set" data="originate_early_media=false"/>
      <action application="set" data="record_stereo=true"/>
      <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
      <action application="set" data="record_name=${uuid}.wav"/>
      <action application="set" data="execute_on_answer=record_session ${record_path}/${record_name}"/>
      <action application="set" data="instant_ringback=true"/>"""
if needle not in t:
    raise SystemExit("dialplan pattern not found")
p.write_text(t.replace(needle, insert, 1))
print("patched inbound recording")
PY

docker cp /tmp/02_skykin_did_ahununu.xml skykin-freeswitch:"$FILE"
mkdir -p /opt/skykin/fs-live
cp -a /tmp/02_skykin_did_ahununu.xml /opt/skykin/fs-live/02_skykin_did_ahununu.xml
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env | cut -d= -f2-)
docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "reloadxml"
docker exec skykin-freeswitch grep -E 'record_path|execute_on_answer' "$FILE"

echo "DONE — inbound records when agent answers (not during welcome/wait)."
