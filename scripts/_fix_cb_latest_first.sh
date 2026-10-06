#!/bin/bash
set -eu
echo "=== Callbacks: latest first ==="
docker exec skykin-web php -r '
$p="/var/www/fusionpbx/app/agent_dashboard/index.php";
$s=file_get_contents($p);
$n=$s;
$n=str_replace("ORDER BY callback_time ASC LIMIT 200","ORDER BY callback_time DESC LIMIT 200",$n);
$n=str_replace("ORDER BY callback_time ASC LIMIT 100","ORDER BY callback_time DESC LIMIT 100",$n);
$n=str_replace(
  "list.sort((a,b) => new Date(a.formatted_time) - new Date(b.formatted_time));",
  "list.sort((a,b) => new Date(b.formatted_time) - new Date(a.formatted_time));",
  $n
);
if ($n===$s) { echo "already DESC or pattern missing\n"; exit(0); }
file_put_contents($p,$n);
echo "index.php patched\n";
'
docker exec skykin-web grep -n "callback_time DESC\|new Date(b.formatted_time)" /var/www/fusionpbx/app/agent_dashboard/index.php | head -10
echo "DONE — hard refresh Callbacks (latest at top)"
