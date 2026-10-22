#!/bin/bash
# Agent-to-agent (two PCs): answer A-leg so DTLS/WebRTC starts, advertise public RTP.
# 1xx only. Does not touch inbound.lua.
set -eu
cd /opt/skykin/skykin-cc-client1 2>/dev/null || cd /opt/skykin-cc-client1 2>/dev/null || true
ESL_PASS=$(grep '^ESL_PASSWORD=' .env 2>/dev/null | cut -d= -f2- || true)
DOMAIN=$(grep '^FS_DOMAIN=' .env 2>/dev/null | cut -d= -f2-)
DOMAIN=${DOMAIN:-client1.skykin.local}
EXT_RTP=$(grep '^EXTERNAL_RTP_IP=' .env 2>/dev/null | cut -d= -f2-)
EXT_RTP=${EXT_RTP:-196.189.237.77}
ESL_PASS=${ESL_PASS:-ClueCon}

MARKER="skykin_a2a_twopc_v1"
cat >/tmp/00_webrtc_local.xml <<EOF
<include>
  <!-- ${MARKER} -->
  <extension name="webrtc_local" continue="false">
    <condition field="destination_number" expression="^(1\\d{2})\$">
      <action application="log" data="NOTICE ${MARKER} dial=\${destination_number}"/>
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="set" data="call_timeout=30"/>
      <action application="set" data="media_webrtc=true"/>
      <action application="set" data="rtp_secure_media=true"/>
      <action application="set" data="rtp_advertise_ip=${EXT_RTP}"/>
      <action application="set" data="include_external_ip=true"/>
      <action application="export" data="media_webrtc=true"/>
      <action application="export" data="rtp_secure_media=true"/>
      <action application="export" data="rtp_advertise_ip=${EXT_RTP}"/>
      <action application="export" data="include_external_ip=true"/>
      <action application="answer"/>
      <action application="bridge" data="{rtp_secure_media=true,media_webrtc=true,rtp_advertise_ip=${EXT_RTP},include_external_ip=true,ignore_early_media=true}user/\$1@${DOMAIN}"/>
    </condition>
  </extension>
</include>
EOF

docker exec skykin-freeswitch mkdir -p "/etc/freeswitch/dialplan/${DOMAIN}" /etc/freeswitch/dialplan/default
docker cp /tmp/00_webrtc_local.xml "skykin-freeswitch:/etc/freeswitch/dialplan/${DOMAIN}/00_webrtc_local.xml"
docker cp /tmp/00_webrtc_local.xml skykin-freeswitch:/etc/freeswitch/dialplan/default/00_webrtc_local.xml

docker exec skykin-freeswitch sh -c "
STAMP=\$(date +%Y%m%d%H%M%S)
for f in /etc/freeswitch/dialplan/${DOMAIN}/*.xml /etc/freeswitch/dialplan/01_skykin_*.xml /etc/freeswitch/dialplan/00_skykin.xml; do
  [ -f \"\$f\" ] || continue
  case \"\$f\" in *00_webrtc_local.xml) continue ;; esac
  if grep -q 'skykin_local_extension' \"\$f\" && grep -q 'user/\$1@' \"\$f\"; then
    echo \"Disable competing skykin_local_extension in \$f\"
    cp -a \"\$f\" \"\$f.bak-twopc-\$STAMP\"
    sed -i 's/name=\"skykin_local_extension\"/name=\"skykin_local_extension_DISABLED\"/' \"\$f\" || true
  fi
done
grep -n 'skykin_a2a_twopc_v1\\|bridge\\|answer' /etc/freeswitch/dialplan/${DOMAIN}/00_webrtc_local.xml
"

docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$ESL_PASS" -x 'reloadxml'
echo "OK twopc ${MARKER} rtp=${EXT_RTP} domain=${DOMAIN}"
echo "Hard-refresh BOTH PCs, dial 1xx, both should hear. During call: show channels → callstate ACTIVE (not EARLY)."
