#!/bin/bash
# Outbound decline diagnostic — no browser session needed. Run on ecs-cc.
# Usage: ./diag_outbound.sh 201 0912345678
set -euo pipefail
EXT="${1:-201}"
DEST="${2:-}"
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env | cut -d= -f2-)
FS() { docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1"; }

echo "=== show channels (text) ==="
FS "show channels"
echo ""
echo "=== show channels as json (agent $EXT / dest ${DEST:-any}) ==="
docker exec skykin-web php -r "
require '/var/www/fusionpbx/app/agent_dashboard/skykin_config.php';
\$ext = preg_replace('/\D+/', '', '$EXT');
\$dest = preg_replace('/\D+/', '', '$DEST');
\$destTail = strlen(\$dest) >= 9 ? substr(\$dest, -9) : \$dest;
\$json = json_decode(skykin_fs_api('show channels as json'), true);
\$rows = is_array(\$json) ? (\$json['rows'] ?? []) : [];
\$agentUuid = ''; \$partnerUuid = ''; \$agentLive = false; \$blegLive = false;
foreach (\$rows as \$row) {
    if (!is_array(\$row)) continue;
    \$name = strtolower((string)(\$row['name'] ?? ''));
    \$cid = preg_replace('/\D+/', '', (string)(\$row['cid_num'] ?? ''));
    \$state = strtoupper((string)(\$row['callstate'] ?? ''));
    if (in_array(\$state, ['HANGUP','DOWN'], true)) continue;
    if (preg_match('#(^|[/@])' . preg_quote(\$ext,'#') . '(@|\$|-)#', \$name) || \$cid === \$ext) {
        \$agentLive = true;
        \$agentUuid = (string)(\$row['uuid'] ?? '');
        \$partnerUuid = trim((string)(\$row['b_uuid'] ?? \$row['bridge_uuid'] ?? ''));
        echo 'AGENT uuid=' . \$agentUuid . ' state=' . \$state . ' b_uuid=' . \$partnerUuid . ' name=' . (\$row['name'] ?? '') . PHP_EOL;
    }
}
if (\$partnerUuid !== '') {
    foreach (\$rows as \$row) {
        if (!is_array(\$row) || (string)(\$row['uuid'] ?? '') !== \$partnerUuid) continue;
        \$state = strtoupper((string)(\$row['callstate'] ?? ''));
        if (!in_array(\$state, ['HANGUP','DOWN'], true)) {
            \$blegLive = true;
            echo 'BLEG uuid=' . \$partnerUuid . ' state=' . \$state . ' name=' . (\$row['name'] ?? '') . ' dest=' . (\$row['dest'] ?? '') . PHP_EOL;
        }
        break;
    }
}
echo json_encode(['agent'=>\$agentLive,'bleg'=>\$blegLive,'agent_uuid'=>\$agentUuid,'partner_uuid'=>\$partnerUuid], JSON_PRETTY_PRINT) . PHP_EOL;
"
