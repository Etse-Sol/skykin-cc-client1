#!/bin/bash
# Alert when softphone bridge fails spike under load.
# Matches: "skykin softphone_fail" from skykin_inbound.lua
# Cron: */2 * * * * /opt/skykin/scripts/skykin_bridge_fail_alert.sh
set -eu

STATE_DIR="${SKYKIN_BRIDGE_FAIL_STATE:-/var/lib/skykin-bridge-fail}"
WINDOW_SEC="${SKYKIN_BRIDGE_FAIL_WINDOW:-600}"
THRESHOLD="${SKYKIN_BRIDGE_FAIL_THRESHOLD:-5}"
COOLDOWN_SEC="${SKYKIN_BRIDGE_FAIL_COOLDOWN:-1800}"
ALERT_TO="${SKYKIN_BRIDGE_FAIL_ALERT_TO:-${SKYKIN_FRAUD_ALERT_TO:-ashineshetu@skykintech.com,solomonetsegenet7@gmail.com}}"

mkdir -p "$STATE_DIR"
NOW=$(date +%s)
LAST="$STATE_DIR/last_alert.ts"
if [ -f "$LAST" ]; then
  PREV=$(cat "$LAST" 2>/dev/null || echo 0)
  if [ $((NOW - PREV)) -lt "$COOLDOWN_SEC" ]; then
    exit 0
  fi
fi

# Recent softphone fails from FreeSWITCH log (container or host bind-mount)
LINES=$(docker exec skykin-freeswitch sh -c \
  "tail -c 8M /var/log/freeswitch/freeswitch.log 2>/dev/null | grep -a 'skykin softphone_fail' | tail -80" \
  2>/dev/null || true)

COUNT=$(printf '%s\n' "$LINES" | grep -c 'skykin softphone_fail' || true)
COUNT=${COUNT:-0}

if [ "$COUNT" -lt "$THRESHOLD" ]; then
  exit 0
fi

SUBJECT="SkyKin softphone fail spike (~$COUNT recent in FS log)"
BODY="Softphone/WebRTC bridge failures (load / dead contact).

Recent count in FS log tail: $COUNT (threshold $THRESHOLD)
Inbound now retries once, rolls agents, then music-waits — callers should not drop instantly.

Check: agents Registered+Ready, skykin-ws-sip, FreeSWITCH.

Recent:
$LINES
"

SMTP_ENV="${SKYKIN_SMTP_ENV:-/opt/skykin/fraud-alert/smtp.env}"
SMTP_PY="${SKYKIN_SMTP_PY:-/opt/skykin/fraud-alert/skykin_send_smtp.py}"
if [ -f "$SMTP_ENV" ] && [ -f "$SMTP_PY" ]; then
  tmp=$(mktemp)
  printf '%s\n' "$BODY" > "$tmp"
  python3 "$SMTP_PY" --env "$SMTP_ENV" --to "$ALERT_TO" --subject "$SUBJECT" --body-file "$tmp" || true
  rm -f "$tmp"
else
  echo "$SUBJECT" >&2
  echo "$BODY" >&2
fi

echo "$NOW" > "$LAST"
