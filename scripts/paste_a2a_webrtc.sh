#!/bin/sh
# Two-PC agent-to-agent WebRTC. 1xx only. Does not change inbound.lua early-answer.
set -eu
DOMAIN=${FS_DOMAIN:-client1.skykin.local}
EXT_RTP=${EXTERNAL_RTP_IP:-196.189.236.103}
ESL_PASS=${ESL_PASSWORD:-ClueCon}
if [ -f /opt/skykin/skykin-cc-client1/.env ]; then
  set -a
  # shellcheck disable=SC1091
  . /opt/skykin/skykin-cc-client1/.env
  set +a
  DOMAIN=${FS_DOMAIN:-$DOMAIN}
  EXT_RTP=${EXTERNAL_RTP_IP:-$EXT_RTP}
  ESL_PASS=${ESL_PASSWORD:-$ESL_PASS}
fi
cat >/tmp/00_webrtc_local.xml <<EOF
<include>
  <extension name="webrtc_local" continue="false">
    <condition field="destination_number" expression="^(1\\d{2})\$">
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="set" data="call_timeout=30"/>
      <action application="set" data="media_webrtc=true"/>
      <action application="set" data="rtp_secure_media=true"/>
      <action application="set" data="rtp_advertise_ip=${EXT_RTP}"/>
      <action application="set" data="include_external_ip=true"/>
      <action application="export" data="media_webrtc=true"/>
      <action application="export" data="rtp_secure_media=true"/>
      <action application="answer"/>
      <action application="bridge" data="{rtp_secure_media=true,media_webrtc=true,rtp_advertise_ip=${EXT_RTP},include_external_ip=true,ignore_early_media=true}user/\$1@${DOMAIN}"/>
    </condition>
  </extension>
</include>
EOF
docker exec skykin-freeswitch mkdir -p "/etc/freeswitch/dialplan/${DOMAIN}" /etc/freeswitch/dialplan/default
docker cp /tmp/00_webrtc_local.xml "skykin-freeswitch:/etc/freeswitch/dialplan/${DOMAIN}/00_webrtc_local.xml"
docker cp /tmp/00_webrtc_local.xml skykin-freeswitch:/etc/freeswitch/dialplan/default/00_webrtc_local.xml
if [ -f docker/freeswitch/scripts/skykin_inbound.lua ]; then
  docker cp docker/freeswitch/scripts/skykin_inbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
fi
docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$ESL_PASS" -x 'reloadxml'
echo "OK A2A webrtc rtp=${EXT_RTP} domain=${DOMAIN}"
