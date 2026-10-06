#!/bin/bash
# Paste/run on ecs-cc as root. Pulls CRM files from GitHub CC repo branch 5.5.
# If repo is private, set GITHUB_TOKEN first:
#   export GITHUB_TOKEN=ghp_your_token_here

set -euo pipefail

DIR=/opt/skykin/app/app/agent_dashboard
BRANCH=5.5
BASE="https://raw.githubusercontent.com/Skykin-Technologies/CC/${BRANCH}/app/agent_dashboard"
STAMP=$(date +%Y%m%d_%H%M%S)

curl_get() {
  local url="$1" out="$2"
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    curl -fsSL -H "Authorization: Bearer ${GITHUB_TOKEN}" -o "$out" "$url"
  else
    curl -fsSL -o "$out" "$url"
  fi
}

for f in crm.php skykin_config.php index.php; do
  [ -f "$DIR/$f" ] && cp -a "$DIR/$f" "$DIR/$f.bak-$STAMP"
done

echo "Downloading from CC/$BRANCH ..."
curl_get "$BASE/crm.php"           "$DIR/crm.php"
curl_get "$BASE/skykin_config.php" "$DIR/skykin_config.php"
curl_get "$BASE/index.php"         "$DIR/index.php"

echo "Verify:"
grep -c deleteContactById "$DIR/crm.php" || true
grep -c skykin_crm_find_contact "$DIR/skykin_config.php" || true
docker exec skykin-web grep -c deleteCrmContact /var/www/fusionpbx/app/agent_dashboard/index.php || true
echo "Done. Hard-refresh browser Ctrl+Shift+R"
