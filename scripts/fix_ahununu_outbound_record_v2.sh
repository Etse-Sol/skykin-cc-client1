#!/bin/bash
# Patch ahununu outbound dialplan to record (record_path/name + record_session).
# Live CDRs today had billsec but empty record_* — dialplan had no record_session.
set -eu

FS_XML=/etc/freeswitch/dialplan/01_skykin_ahununu.xml
docker cp skykin-freeswitch:"$FS_XML" /tmp/01_skykin_ahununu.xml
cp -a /tmp/01_skykin_ahununu.xml /tmp/01_skykin_ahununu.xml.bak.$(date +%H%M%S)

python3 <<'PY'
from pathlib import Path
p = Path("/tmp/01_skykin_ahununu.xml")
t = p.read_text()
if t.count("record_session") >= 4 and "record_path=/var/lib/freeswitch/recordings/ahununu" in t:
    print("already has record_session x%d — nothing to do" % t.count("record_session"))
    raise SystemExit(0)

# Insert recording block after every outbound pre_answer that lacks record_session nearby.
old = """        <action application="pre_answer"/>
        <action application="set" data="bleg_uuid=${create_uuid()}"/>"""
new = """        <action application="pre_answer"/>
        <action application="export" data="domain_name=ahununu"/>
        <action application="set" data="record_stereo=true"/>
        <action application="system" data="mkdir -p /var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
        <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
        <action application="set" data="record_name=${uuid}.wav"/>
        <action application="export" data="record_path=${record_path}"/>
        <action application="export" data="record_name=${record_name}"/>
        <action application="record_session" data="${record_path}/${record_name}"/>
        <action application="set" data="bleg_uuid=${create_uuid()}"/>"""

# Also match variants that already export domain or set call_direction between lines
old2 = """        <action application="pre_answer"/>
        <action application="export" data="domain_name=ahununu"/>
        <action application="set" data="bleg_uuid=${create_uuid()}"/>"""
new2 = """        <action application="pre_answer"/>
        <action application="export" data="domain_name=ahununu"/>
        <action application="set" data="record_stereo=true"/>
        <action application="system" data="mkdir -p /var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
        <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
        <action application="set" data="record_name=${uuid}.wav"/>
        <action application="export" data="record_path=${record_path}"/>
        <action application="export" data="record_name=${record_name}"/>
        <action application="record_session" data="${record_path}/${record_name}"/>
        <action application="set" data="bleg_uuid=${create_uuid()}"/>"""

n = 0
if old in t:
    t = t.replace(old, new)
    n += 1
if old2 in t:
    t = t.replace(old2, new2)
    n += 1

# Fallback: after each pre_answer inside outbound extensions, inject if missing
import re
def inject(m):
    block = m.group(0)
    if "record_session" in block:
        return block
    return block.replace(
        '<action application="pre_answer"/>',
        '''<action application="pre_answer"/>
        <action application="export" data="domain_name=ahununu"/>
        <action application="set" data="record_stereo=true"/>
        <action application="system" data="mkdir -p /var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
        <action application="set" data="record_path=/var/lib/freeswitch/recordings/ahununu/archive/${strftime(%Y)}/${strftime(%b)}/${strftime(%d)}"/>
        <action application="set" data="record_name=${uuid}.wav"/>
        <action application="export" data="record_path=${record_path}"/>
        <action application="export" data="record_name=${record_name}"/>
        <action application="record_session" data="${record_path}/${record_name}"/>''',
        1,
    )

t2, count = re.subn(
    r'<extension name="skykin_outbound_[^"]+">.*?</extension>',
    inject,
    t,
    flags=re.S,
)
if count:
    t = t2
    n += count

p.write_text(t)
print("patched ok; record_session count=%d" % t.count("record_session"))
if t.count("record_session") < 1:
    raise SystemExit("FAILED: still no record_session — paste dialplan outbound snippet")
PY

docker cp /tmp/01_skykin_ahununu.xml skykin-freeswitch:"$FS_XML"
mkdir -p /opt/skykin/fs-live
cp -a /tmp/01_skykin_ahununu.xml /opt/skykin/fs-live/01_skykin_ahununu.xml

PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env 2>/dev/null | cut -d= -f2-)
[ -z "$PW" ] && PW=ClueCon
docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "reloadxml"
docker exec skykin-freeswitch mkdir -p /var/lib/freeswitch/recordings/ahununu/archive

echo "=== verify ==="
docker exec skykin-freeswitch grep -c record_session /etc/freeswitch/dialplan/01_skykin_ahununu.xml
docker exec skykin-freeswitch grep -n 'record_session\|record_path' /etc/freeswitch/dialplan/01_skykin_ahununu.xml | head -30
echo "DONE — make one answered outbound call, then:"
echo "  docker exec skykin-freeswitch ls -lt /var/lib/freeswitch/recordings/ahununu/archive/\$(date +%Y/%b/%d)/ | head"
