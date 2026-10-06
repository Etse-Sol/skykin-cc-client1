#!/bin/bash
# SkyKin — today from 08:00 (EAT) status using live CDR labels
set -euo pipefail
DOMAIN="${1:-ahununu}"
docker exec skykin-web php -r "
require '/var/www/fusionpbx/app/agent_dashboard/skykin_config.php';
\$domain = getenv('SKYKIN_DOMAIN') ?: '$DOMAIN';
\$tz = new DateTimeZone('Africa/Addis_Ababa');
\$now = new DateTime('now', \$tz);
\$from = new DateTime(\$now->format('Y-m-d') . ' 08:00:00', \$tz);
\$ts = \$from->getTimestamp();
\$te = \$now->getTimestamp();
echo 'Domain: ' . \$domain . PHP_EOL;
echo 'From:   ' . \$from->format('Y-m-d H:i:s T') . PHP_EOL;
echo 'To:     ' . \$now->format('Y-m-d H:i:s T') . PHP_EOL;
echo str_repeat('-', 56) . PHP_EOL;
try {
  \$db = skykin_db();
} catch (Throwable \$e) {
  // FusionPBX PDO helper name may differ
  \$db = null;
}
if (!\$db) {
  \$conf = '/etc/fusionpbx/config.conf';
  \$h='127.0.0.1'; \$p='5432'; \$n='fusionpbx'; \$u='fusionpbx'; \$pw='';
  if (file_exists(\$conf)) foreach (file(\$conf) as \$ln) {
    if (preg_match('/^\\s*database\\.0\\.(host|port|name|username|password)\\s*=\\s*(.*)\$/', trim(\$ln), \$m)) {
      \$k=\$m[1]; \$v=trim(\$m[2]);
      if (\$k==='host') \$h=\$v; elseif (\$k==='port') \$p=\$v; elseif (\$k==='name') \$n=\$v;
      elseif (\$k==='username') \$u=\$v; elseif (\$k==='password') \$pw=\$v;
    }
  }
  \$db = new PDO(\"pgsql:host=\$h;port=\$p;dbname=\$n\", \$u, \$pw, [PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION]);
}
\$rows = skykin_cdr_fetch_period(\$db, \$domain, \$ts, \$te);
\$m = skykin_cdr_period_metrics(\$rows);
\$failed=0; \$busy=0; \$other=0; \$withRec=0; \$ansNoRec=0;
\$byLabel=[];
foreach (\$rows as \$r) {
  \$lab = skykin_cdr_result_label(\$r);
  \$byLabel[\$lab] = (\$byLabel[\$lab] ?? 0) + 1;
  if (\$lab === 'Failed') \$failed++;
  elseif (\$lab === 'Agent Busy') \$busy++;
  elseif (!in_array(\$lab, ['Answered','Abandoned','Missed'], true)) \$other++;
  \$rec = trim((string)(\$r['record_name'] ?? ''));
  if (\$rec !== '') \$withRec++;
  if (\$lab === 'Answered' && \$rec === '') \$ansNoRec++;
}
printf(\"Calls (collapsed): %d\\n\", (int)\$m['total']);
printf(\"Answered:          %d\\n\", (int)\$m['answered']);
printf(\"Abandoned:         %d\\n\", (int)\$m['abandoned']);
printf(\"Missed:            %d\\n\", (int)\$m['missed']);
printf(\"Failed (out):      %d\\n\", \$failed);
printf(\"Agent Busy:        %d\\n\", \$busy);
printf(\"Avg talk:          %s\\n\", skykin_cdr_fmt_dur((int)(\$m['avg_dur'] ?? 0)));
printf(\"Recordings linked: %d\\n\", \$withRec);
printf(\"Answered w/o file: %d\\n\", \$ansNoRec);
echo str_repeat('-', 56) . PHP_EOL;
echo \"By label:\\n\";
foreach (\$byLabel as \$k=>\$v) echo \"  \$k: \$v\\n\";
echo str_repeat('-', 56) . PHP_EOL;
echo \"Latest 15 rows:\\n\";
\$i=0;
foreach (\$rows as \$r) {
  if (\$i++ >= 15) break;
  \$lab = skykin_cdr_result_label(\$r);
  \$rec = trim((string)(\$r['record_name'] ?? '')) !== '' ? 'rec' : '-';
  printf(\"  %s  %-10s  %s -> %s  %s  %s\\n\",
    \$r['call_time'] ?? '',
    \$lab,
    \$r['caller_id_number'] ?? '',
    \$r['destination_number'] ?? '',
    skykin_cdr_fmt_dur(skykin_cdr_display_sec(\$r)),
    \$rec
  );
}
"
