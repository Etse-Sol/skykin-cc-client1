#!/bin/bash
# Ahununu inbound IVR on ecs-cc (paste as root).
# Call path: DID 8414/035-039 -> blacklist -> skykin_inbound.lua (welcome inside lua) -> agents
# Do NOT use transfer 500 — FusionPBX dialplan is not bound on this stack.
set -eu

PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env | cut -d= -f2-)
FS() { docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1"; }
ROOT="${SKYKIN_DEPLOY_REF:-https://raw.githubusercontent.com/Etse-Sol/skykin-fusionpbx/5.5}"
LIVE=/opt/skykin/fs-live
mkdir -p "$LIVE"

curl_get() {
  local url="$1" out="$2"
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    curl -fSL -H "Authorization: Bearer ${GITHUB_TOKEN}" -o "$out" "$url"
  else
    curl -fSL -o "$out" "$url"
  fi
}

echo "==> 1) Lua scripts (welcome + inbound)"
for f in skykin_welcome.lua skykin_inbound.lua; do
  curl_get "$ROOT/docker/freeswitch/scripts/$f" "/tmp/$f"
  docker cp "/tmp/$f" "skykin-freeswitch:/etc/freeswitch/scripts/$f"
  cp "/tmp/$f" "$LIVE/$f"
done

echo "==> 2) Public inbound DID -> skykin_inbound.lua (NOT transfer 500)"
docker exec -i skykin-freeswitch tee /etc/freeswitch/dialplan/public/02_skykin_did_ahununu.xml >/dev/null <<'EOF'
<include>
  <extension name="skykin_inbound_did_ahununu">
    <condition field="destination_number" expression="^(\+?(?:251)?0?11619803[5-9]|8414|\+?(?:251)?0?116901313)$" break="on-false">
      <action application="set" data="rtcp_audio_interval_msec=0"/>
      <action application="set" data="rtp_advertise_ip=10.0.0.77"/>
      <action application="set" data="include_external_ip=false"/>
      <action application="set" data="rtp_secure_media=false"/>
      <action application="set" data="media_webrtc=false"/>
      <action application="set" data="domain_name=ahununu"/>
      <action application="export" data="domain_name=ahununu"/>
      <action application="set" data="call_direction=inbound"/>
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=false"/>
      <action application="set" data="ignore_early_media=true"/>
      <action application="set" data="bridge_early_media=false"/>
      <action application="set" data="originate_early_media=false"/>
      <action application="set" data="instant_ringback=true"/>
      <action application="lua" data="/etc/freeswitch/scripts/skykin_cc_prune.lua 8000@ahununu"/>
      <action application="export" data="nolocal:execute_on_hangup=lua::/etc/freeswitch/scripts/skykin_cc_drop.lua"/>
      <action application="set" data="cc_export_vars=execute_on_hangup"/>
      <action application="lua" data="/etc/freeswitch/scripts/skykin_bl_gate.lua"/>
    </condition>
    <condition field="${skykin_blocked}" expression="^true$" break="on-true">
      <action application="hangup" data="CALL_REJECTED"/>
    </condition>
    <condition>
      <action application="ring_ready"/>
      <action application="lua" data="/etc/freeswitch/scripts/skykin_inbound.lua"/>
    </condition>
  </extension>
</include>
EOF

docker cp skykin-freeswitch:/etc/freeswitch/dialplan/public/02_skykin_did_ahununu.xml "$LIVE/02_skykin_did_ahununu.xml"

FS "reloadxml"
docker exec skykin-freeswitch fs_cli -x "reload mod_lua" 2>/dev/null || true

echo "==> DONE"
echo "Recordings: ahununu-opening.wav / ahununu-waiting.wav under /var/lib/freeswitch/recordings/ahununu/"
echo "Test: agent 201 Ready, call 8414 — logs should show skykin welcome play then skykin inbound try"
