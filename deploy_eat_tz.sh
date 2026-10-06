#!/bin/bash
# Apply Ethiopia (EAT) timezone to agent + supervisor call logs — no GitHub required.
set -eu

WEB=skykin-web
DASH=/var/www/fusionpbx/app/agent_dashboard
TMP=/tmp/skykin_eat_tz
mkdir -p "$TMP"

for f in skykin_config.php index.php supervisor.php data.php crm.php evaluation.php; do
  docker cp "$WEB:$DASH/$f" "$TMP/$f"
  cp -a "$TMP/$f" "$TMP/${f}.bak"
done

python3 <<'PY'
from pathlib import Path

tmp = Path("/tmp/skykin_eat_tz")
cfg = tmp / "skykin_config.php"
text = cfg.read_text(encoding="utf-8", errors="replace")

helpers = '''
/** Postgres-safe IANA zone name for SQL fragments. */
function skykin_sql_tz(): string {
\treturn str_replace("'", "''", skykin_timezone());
}

/** Local wall-clock instant from a Unix epoch column (v_xml_cdr.start_epoch). */
function skykin_cdr_local_ts_sql(string $epoch_col = 'start_epoch'): string {
\t$tz = skykin_sql_tz();
\treturn "timezone('{$tz}', to_timestamp({$epoch_col}))";
}

/** Format a CDR epoch in the dashboard timezone. */
function skykin_cdr_time_sql(string $pg_format, string $epoch_col = 'start_epoch'): string {
\treturn 'to_char(' . skykin_cdr_local_ts_sql($epoch_col) . ", '{$pg_format}')";
}

/** Format a timestamptz column in the dashboard timezone. */
function skykin_db_time_sql(string $pg_format, string $ts_col): string {
\t$tz = skykin_sql_tz();
\treturn "to_char(timezone('{$tz}', {$ts_col}), '{$pg_format}')";
}
'''

if "function skykin_cdr_time_sql" not in text:
    old = "\t$tz = date_default_timezone_get() ?: 'UTC';\n\treturn $tz;\n}"
    new = "\t$tz = date_default_timezone_get() ?: 'UTC';\n\tif (strcasecmp($tz, 'UTC') === 0 || strcasecmp($tz, 'Etc/UTC') === 0) {\n\t\t$tz = 'Africa/Addis_Ababa';\n\t}\n\treturn $tz;\n}" + helpers
    if old not in text:
        raise SystemExit("skykin_config.php: expected timezone block not found")
    text = text.replace(old, new, 1)

old_fetch = """\t$s = $db->prepare(
\t\t\"SELECT start_epoch,
\t\t\tto_char(to_timestamp(start_epoch),'YYYY-MM-DD HH24:MI') as call_time,
\t\t\tto_char(to_timestamp(start_epoch),'YYYY-MM-DD') as call_day,
\t\t\tEXTRACT(DOW FROM to_timestamp(start_epoch))::int as dow,
\t\t\tEXTRACT(HOUR FROM to_timestamp(start_epoch))::int as hour,"""
new_fetch = """\t$local_ts = skykin_cdr_local_ts_sql();
\t$s = $db->prepare(
\t\t\"SELECT start_epoch,
\t\t\t\" . skykin_cdr_time_sql('YYYY-MM-DD HH24:MI') . \" as call_time,
\t\t\t\" . skykin_cdr_time_sql('YYYY-MM-DD') . \" as call_day,
\t\t\tEXTRACT(DOW FROM {$local_ts})::int as dow,
\t\t\tEXTRACT(HOUR FROM {$local_ts})::int as hour,"""
if old_fetch in text:
    text = text.replace(old_fetch, new_fetch, 1)

cfg.write_text(text, encoding="utf-8")

replacements = [
    ("to_char(to_timestamp(start_epoch),'YYYY-MM-DD HH24:MI')", "\" . skykin_cdr_time_sql('YYYY-MM-DD HH24:MI') . \""),
    ("to_char(to_timestamp(start_epoch),'HH24:MI')", "\" . skykin_cdr_time_sql('HH24:MI') . \""),
    ("to_char(to_timestamp(start_epoch), 'HH24:MI')", "\" . skykin_cdr_time_sql('HH24:MI') . \""),
    ("to_char(created_at,'YYYY-MM-DD HH24:MI')", "\" . skykin_db_time_sql('YYYY-MM-DD HH24:MI', 'created_at') . \""),
    ("to_char(requested_at, 'YYYY-MM-DD HH24:MI')", "\" . skykin_db_time_sql('YYYY-MM-DD HH24:MI', 'requested_at') . \""),
]

for name in ["index.php", "supervisor.php", "data.php", "crm.php", "evaluation.php"]:
    p = tmp / name
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    for old, new in replacements:
        t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")

print("patched OK")
PY

for f in skykin_config.php index.php supervisor.php data.php crm.php evaluation.php; do
  docker cp "$TMP/$f" "$WEB:$DASH/$f"
done

docker exec "$WEB" php -l "$DASH/skykin_config.php"
docker exec "$WEB" php -l "$DASH/index.php"
docker exec "$WEB" php -l "$DASH/supervisor.php"

grep -q '^SKYKIN_TZ=' /opt/skykin/app/.env \
  && sed -i 's|^SKYKIN_TZ=.*|SKYKIN_TZ=Africa/Addis_Ababa|' /opt/skykin/app/.env \
  || echo 'SKYKIN_TZ=Africa/Addis_Ababa' >> /opt/skykin/app/.env

echo "DONE — hard refresh dashboard (Ctrl+Shift+R). Backups in $TMP/*.bak"
