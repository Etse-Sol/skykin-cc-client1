#!/bin/bash
# Deploy fixed longest-idle skykin_inbound.lua into running FreeSWITCH container.
# Run on ecs-cc as root, from a directory that has the new lua file,
# OR paste after uploading the file to /tmp/skykin_inbound.lua
set -euo pipefail
SRC="${1:-/tmp/skykin_inbound.lua}"
if [ ! -f "$SRC" ]; then
  echo "Missing $SRC — upload the new skykin_inbound.lua first"
  exit 1
fi
docker cp "$SRC" skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
# Persist if host overlay is used
if [ -d /root/skykin-fs-etc/scripts ]; then
  cp "$SRC" /root/skykin-fs-etc/scripts/skykin_inbound.lua
  echo "Also copied to /root/skykin-fs-etc/scripts/"
fi
docker exec skykin-freeswitch ls -la /etc/freeswitch/scripts/skykin_inbound.lua
docker exec skykin-freeswitch grep -n "True longest-idle\|skykin_agent_idle\|agent_idle_stamp" \
  /etc/freeswitch/scripts/skykin_inbound.lua | head -20
echo "Deployed. Next inbound calls will log: skykin longest-idle order ... b= o= r= h="
echo "No FreeSWITCH restart required (Lua reloads per call)."
