#!/bin/bash
# Enable FreeSWITCH recording on ahununu outbound (SIP8035/758/759).
# Inbound + agent-local already record; outbound was missing record_session.
set -eu

REC='        <action application="export" data="domain_name=ahununu"/>
        <action application="set" data="record_stereo=true"/>
        <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
        <action application="set" data="record_name=${uuid}.wav"/>
        <action application="record_session" data="${record_path}/${record_name}"/>'

docker cp skykin-freeswitch:/etc/freeswitch/dialplan/01_skykin_ahununu.xml /tmp/01_skykin_ahununu.xml
cp -a /tmp/01_skykin_ahununu.xml /tmp/01_skykin_ahununu.xml.bak

python3 <<'PY'
from pathlib import Path
p = Path("/tmp/01_skykin_ahununu.xml")
t = p.read_text()
needle = """        <action application="pre_answer"/>
        <action application="set" data="bleg_uuid=${create_uuid()}"/>"""
insert = """        <action application="pre_answer"/>
        <action application="export" data="domain_name=ahununu"/>
        <action application="set" data="record_stereo=true"/>
        <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
        <action application="set" data="record_name=${uuid}.wav"/>
        <action application="record_session" data="${record_path}/${record_name}"/>
        <action application="set" data="bleg_uuid=${create_uuid()}"/>"""
if "record_session" in t and "skykin_outbound_et_zero" in t:
    # Already patched — count outbound blocks with record_session after pre_answer
    n = t.count('skykin_outbound')
    r = t.count('record_session')
    if r >= 3:
        print("already patched (%d record_session)" % r)
        raise SystemExit(0)
if needle not in t:
    raise SystemExit("dialplan pattern not found — paste 01_skykin_ahununu.xml snippet")
p.write_text(t.replace(needle, insert))
print("patched", t.count(needle), "outbound blocks")
PY

docker cp /tmp/01_skykin_ahununu.xml skykin-freeswitch:/etc/freeswitch/dialplan/01_skykin_ahununu.xml
mkdir -p /opt/skykin/fs-live
cp -a /tmp/01_skykin_ahununu.xml /opt/skykin/fs-live/01_skykin_ahununu.xml
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env | cut -d= -f2-)
docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "reloadxml"
docker exec skykin-freeswitch mkdir -p /var/lib/freeswitch/recordings/ahununu/archive
docker exec skykin-freeswitch grep -c record_session /etc/freeswitch/dialplan/01_skykin_ahununu.xml

echo "DONE — place one outbound test call, then:"
echo "  ls -la /var/lib/freeswitch/recordings/ahununu/archive/\$(date +%Y/%b/%d)/  # inside FS container"
echo "  docker exec skykin-freeswitch find /var/lib/freeswitch/recordings/ahununu/archive -name '*.wav' -mmin -5"
