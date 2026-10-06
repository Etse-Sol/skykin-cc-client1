#!/bin/bash
# SkyKin fraud alert monitor — SIP scanner INVITEs + suspicious answered outbound.
# Install on ecs-cc (see install block at bottom). LF endings only.
set -eu

ALERT_TO="${SKYKIN_FRAUD_ALERT_TO:-ashineshetu@skykintech.com,solomonetsegenet7@gmail.com}"
STATE_DIR="${SKYKIN_FRAUD_STATE:-/var/lib/skykin-fraud}"
LOG_FS="/var/log/freeswitch/freeswitch.log"
COOLDOWN_SEC="${SKYKIN_FRAUD_COOLDOWN:-3600}"
MIN_BILLSEC="${SKYKIN_FRAUD_MIN_BILLSEC:-5}"

mkdir -p "$STATE_DIR"
SENT="$STATE_DIR/sent.keys"
touch "$SENT"
NOW=$(date +%s)

# prune old cooldown keys (7 days)
if [ -s "$SENT" ]; then
  awk -v now="$NOW" -v keep=604800 'NF>=2 && (now-$2)<keep {print}' "$SENT" > "$SENT.tmp" || true
  mv -f "$SENT.tmp" "$SENT"
fi

already_sent() {
  local key="$1"
  awk -v k="$key" -v now="$NOW" -v cd="$COOLDOWN_SEC" '
    $1==k && (now-$2)<cd { found=1 }
    END { exit found?0:1 }
  ' "$SENT"
}

mark_sent() {
  echo "$1 $NOW" >> "$SENT"
}

send_mail() {
  local subject="$1"
  local body="$2"
  local from="${SKYKIN_FRAUD_FROM:-}"
  local smtp_env="${SKYKIN_SMTP_ENV:-/opt/skykin/fraud-alert/smtp.env}"
  local smtp_py="${SKYKIN_SMTP_PY:-/opt/skykin/fraud-alert/skykin_send_smtp.py}"

  # Prefer real SMTP (notifications@skykintech.com.et)
  if [ -f "$smtp_env" ] && [ -f "$smtp_py" ]; then
    local tmp
    tmp=$(mktemp)
    printf '%s\n' "$body" > "$tmp"
    if python3 "$smtp_py" --env "$smtp_env" --to "$ALERT_TO" --subject "$subject" --body-file "$tmp"; then
      rm -f "$tmp"
      return 0
    fi
    rm -f "$tmp"
  fi

  from="${from:-skykin-fraud@$(hostname -f 2>/dev/null || echo ecs-cc)}"
  if command -v mail >/dev/null 2>&1; then
    printf '%s\n' "$body" | mail -s "$subject" -r "$from" "$ALERT_TO" && return 0
  fi
  if command -v sendmail >/dev/null 2>&1; then
    {
      echo "To: $ALERT_TO"
      echo "From: $from"
      echo "Subject: $subject"
      echo "Content-Type: text/plain; charset=UTF-8"
      echo
      printf '%s\n' "$body"
    } | sendmail -t && return 0
  fi
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx skykin-web; then
    docker exec -e SUBJ="$subject" -e BODY="$body" -e TO="$ALERT_TO" -e FROM="$from" skykin-web \
      php -r '
        $to=getenv("TO"); $subj=getenv("SUBJ"); $body=getenv("BODY"); $from=getenv("FROM");
        $headers="From: ".$from."\r\nContent-Type: text/plain; charset=UTF-8";
        exit(mail($to,$subj,$body,$headers)?0:1);
      ' && return 0
  fi
  echo "WARN: no SMTP/mail transport" >&2
  return 1
}

alert() {
  local key="$1"
  local subject="$2"
  local body="$3"
  if already_sent "$key"; then
    return 0
  fi
  if send_mail "$subject" "$body"; then
    mark_sent "$key"
    echo "ALERT sent: $subject"
  else
    echo "ALERT FAILED: $subject" >&2
  fi
}

# --- 1) SIP scanner / odd external INVITEs (like 172.86.92.151 / 1001) ---
# Look at recent FS log lines (last ~8000) for sofia/external invites from public IPs
# dialing long international-style destinations.
SCAN_FILE="$STATE_DIR/last_scan_line"
LAST_SCAN=0
[ -f "$SCAN_FILE" ] && LAST_SCAN=$(cat "$SCAN_FILE" 2>/dev/null || echo 0)

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx skykin-freeswitch; then
  # dump recent external invite notices
  TMP="$STATE_DIR/ext_invite.tmp"
  docker exec skykin-freeswitch sh -c \
    'tail -n 8000 /var/log/freeswitch/freeswitch.log 2>/dev/null | grep -E "sofia/external/.+receiving invite from|New Channel sofia/external/" || true' \
    > "$TMP" 2>/dev/null || true

  # Parse: IP + caller-like user
  while IFS= read -r line; do
    ip=$(printf '%s\n' "$line" | sed -n 's/.*from \([0-9.]*\):[0-9]*.*/\1/p')
    [ -z "$ip" ] && ip=$(printf '%s\n' "$line" | sed -n 's/.*sofia\/external\/[^@]*@\([0-9.]*\).*/\1/p')
    user=$(printf '%s\n' "$line" | sed -n 's/.*sofia\/external\/\([^@/ ]*\)@.*/\1/p')
    [ -z "$ip" ] && continue
    # skip private / docker / our known LAN
    case "$ip" in
      127.*|10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[0-1].*|196.189.236.*) continue ;;
    esac
    key="sipscan:$ip:$user"
    alert "$key" \
      "[SkyKin] SIP scan attempt from $ip" \
      "Time: $(date -Is)
Host: $(hostname)
Type: inbound sofia/external INVITE (scanner / toll-fraud probe)
Source IP: $ip
From-user: ${user:-unknown}

This is usually a fraud scanner. Confirm it did NOT bridge to your trunk.
Sample log line:
$line
"
  done < "$TMP"
  rm -f "$TMP"
fi

# --- 2) Suspicious answered outbound (non-Ethiopia / long intl) ---
# Ethiopia domestic patterns we allow: +251 / 251 / 09 / 07 / 011 / hunt DIDs / short ext
SQL=$(cat <<'SQL'
SELECT xml_cdr_uuid::text,
       start_stamp::text,
       COALESCE(direction,''),
       COALESCE(caller_id_number,''),
       COALESCE(destination_number,''),
       COALESCE(billsec,0)::int,
       COALESCE(hangup_cause,'')
FROM v_xml_cdr
WHERE start_stamp >= NOW() - INTERVAL '15 minutes'
  AND COALESCE(billsec,0)::int >= __MIN_BILL__
  AND (
    direction ILIKE '%out%'
    OR (destination_number ~ '^[+0-9]{8,}$' AND length(regexp_replace(destination_number,'\D','','g')) >= 10)
  )
  AND destination_number !~* '^(?:\\+?251|0?9[0-9]{8}|0?7[0-9]{8}|0?11[0-9]{7,}|11619803[5-9]|8000|20[0-9]|10[0-9]|8414)'
ORDER BY start_stamp DESC
LIMIT 40;
SQL
)
SQL=${SQL/__MIN_BILL__/$MIN_BILLSEC}

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx skykin-db; then
  docker exec skykin-db psql -U fusionpbx -d fusionpbx -At -F '|' -c "$SQL" 2>/dev/null | while IFS='|' read -r uuid stamp dir cid dest bill cause; do
    [ -z "${uuid:-}" ] && continue
    key="out:$uuid"
    alert "$key" \
      "[SkyKin] Suspicious outbound answered: $dest" \
      "Time: $stamp
Direction: $dir
Caller: $cid
Destination: $dest
Talk seconds: $bill
Hangup: $cause
CDR uuid: $uuid

Review this call in supervisor CDR / recordings.
"
  done
fi

echo "skykin-fraud-alert OK $(date -Is)"
