#!/bin/bash
# Install SkyKin fraud email alerts on ecs-cc. LF only.
set -eu

ALERT_TO='ashineshetu@skykintech.com,solomonetsegenet7@gmail.com'
DIR=/opt/skykin/fraud-alert
mkdir -p "$DIR" /var/lib/skykin-fraud

# Embedded monitor (same as scripts/skykin_fraud_alert.sh)
cat > "$DIR/skykin_fraud_alert.sh" <<'MONITOR'
#!/bin/bash
set -eu
ALERT_TO="${SKYKIN_FRAUD_ALERT_TO:-ashineshetu@skykintech.com,solomonetsegenet7@gmail.com}"
STATE_DIR="${SKYKIN_FRAUD_STATE:-/var/lib/skykin-fraud}"
COOLDOWN_SEC="${SKYKIN_FRAUD_COOLDOWN:-3600}"
MIN_BILLSEC="${SKYKIN_FRAUD_MIN_BILLSEC:-5}"
mkdir -p "$STATE_DIR"
SENT="$STATE_DIR/sent.keys"
touch "$SENT"
NOW=$(date +%s)
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
mark_sent() { echo "$1 $NOW" >> "$SENT"; }
send_mail() {
  local subject="$1" body="$2"
  local from="${SKYKIN_FRAUD_FROM:-skykin-fraud@$(hostname -f 2>/dev/null || echo ecs-cc)}"
  if command -v mail >/dev/null 2>&1; then
    printf '%s\n' "$body" | mail -s "$subject" -r "$from" "$ALERT_TO" && return 0
  fi
  if command -v sendmail >/dev/null 2>&1; then
    { echo "To: $ALERT_TO"; echo "From: $from"; echo "Subject: $subject"; echo "Content-Type: text/plain; charset=UTF-8"; echo; printf '%s\n' "$body"; } | sendmail -t && return 0
  fi
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx skykin-web; then
    docker exec -e SUBJ="$subject" -e BODY="$body" -e TO="$ALERT_TO" -e FROM="$from" skykin-web \
      php -r '$to=getenv("TO"); $subj=getenv("SUBJ"); $body=getenv("BODY"); $from=getenv("FROM"); $headers="From: ".$from."\r\nContent-Type: text/plain; charset=UTF-8"; exit(mail($to,$subj,$body,$headers)?0:1);' && return 0
  fi
  echo "WARN: no mail transport" >&2
  return 1
}
alert() {
  local key="$1" subject="$2" body="$3"
  already_sent "$key" && return 0
  if send_mail "$subject" "$body"; then mark_sent "$key"; echo "ALERT sent: $subject"; else echo "ALERT FAILED: $subject" >&2; fi
}

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx skykin-freeswitch; then
  TMP="$STATE_DIR/ext_invite.tmp"
  docker exec skykin-freeswitch sh -c 'tail -n 8000 /var/log/freeswitch/freeswitch.log 2>/dev/null | grep -E "sofia/external/.+receiving invite from|New Channel sofia/external/" || true' > "$TMP" 2>/dev/null || true
  while IFS= read -r line; do
    ip=$(printf '%s\n' "$line" | sed -n 's/.*from \([0-9.]*\):[0-9]*.*/\1/p')
    [ -z "$ip" ] && ip=$(printf '%s\n' "$line" | sed -n 's/.*sofia\/external\/[^@]*@\([0-9.]*\).*/\1/p')
    user=$(printf '%s\n' "$line" | sed -n 's/.*sofia\/external\/\([^@/ ]*\)@.*/\1/p')
    [ -z "$ip" ] && continue
    case "$ip" in
      127.*|10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[0-1].*|196.189.236.*) continue ;;
    esac
    alert "sipscan:$ip:$user" "[SkyKin] SIP scan attempt from $ip" "Time: $(date -Is)
Host: $(hostname)
Type: inbound sofia/external INVITE (scanner / toll-fraud probe)
Source IP: $ip
From-user: ${user:-unknown}

Sample:
$line
"
  done < "$TMP"
  rm -f "$TMP"
fi

SQL=$(cat <<SQL
SELECT xml_cdr_uuid::text, start_stamp::text, COALESCE(direction,''), COALESCE(caller_id_number,''), COALESCE(destination_number,''), COALESCE(billsec,0)::int, COALESCE(hangup_cause,'')
FROM v_xml_cdr
WHERE start_stamp >= NOW() - INTERVAL '15 minutes'
  AND COALESCE(billsec,0)::int >= $MIN_BILLSEC
  AND (
    direction ILIKE '%out%'
    OR (destination_number ~ '^[+0-9]{8,}$' AND length(regexp_replace(destination_number,'\\D','','g')) >= 10)
  )
  AND destination_number !~* '^(?:\\+?251|0?9[0-9]{8}|0?7[0-9]{8}|0?11[0-9]{7,}|11619803[5-9]|8000|20[0-9]|10[0-9]|8414)'
ORDER BY start_stamp DESC
LIMIT 40;
SQL
)

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx skykin-db; then
  docker exec skykin-db psql -U fusionpbx -d fusionpbx -At -F '|' -c "$SQL" 2>/dev/null | while IFS='|' read -r uuid stamp dir cid dest bill cause; do
    [ -z "${uuid:-}" ] && continue
    alert "out:$uuid" "[SkyKin] Suspicious outbound answered: $dest" "Time: $stamp
Direction: $dir
Caller: $cid
Destination: $dest
Talk seconds: $bill
Hangup: $cause
CDR uuid: $uuid
"
  done
fi
echo "skykin-fraud-alert OK $(date -Is)"
MONITOR

chmod +x "$DIR/skykin_fraud_alert.sh"
cat > /etc/cron.d/skykin-fraud-alert <<EOF
# SkyKin fraud alerts every 5 minutes
*/5 * * * * root SKYKIN_FRAUD_ALERT_TO='$ALERT_TO' $DIR/skykin_fraud_alert.sh >> /var/log/skykin-fraud-alert.log 2>&1
EOF
chmod 644 /etc/cron.d/skykin-fraud-alert

echo "Installed. Recipients: $ALERT_TO"
echo "Running once now..."
SKYKIN_FRAUD_ALERT_TO="$ALERT_TO" "$DIR/skykin_fraud_alert.sh" || true
echo
echo "Check log: tail -20 /var/log/skykin-fraud-alert.log"
echo "Test mail (optional):"
echo "  echo test | mail -s 'SkyKin fraud test' ashineshetu@skykintech.com"
echo "DONE"
