#!/usr/bin/env python3
"""Build restore_full_inbound_ah.sh with embedded full skykin_inbound.lua."""
from pathlib import Path
import base64

root = Path(r"C:\Users\hp\skykin-fusionpbx")
lua = (root / "docker/freeswitch/scripts/skykin_inbound.lua").read_bytes().replace(b"\r\n", b"\n")
b64 = base64.b64encode(lua).decode("ascii")
chunks = "\n".join(b64[i : i + 76] for i in range(0, len(b64), 76))

script = f"""#!/bin/bash
# Restore full ahununu skykin_inbound.lua + bypass after-hours for testing
set -euo pipefail
B64=$(cat <<'B64EOF'
{chunks}
B64EOF
)
echo "$B64" | base64 -d > /tmp/skykin_inbound.lua.full
grep -q 'ALWAYS WebRTC' /tmp/skykin_inbound.lua.full
grep -q 'outside_business_hours' /tmp/skykin_inbound.lua.full
grep -q 'retry once' /tmp/skykin_inbound.lua.full
wc -l /tmp/skykin_inbound.lua.full

docker cp skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua \\
  /tmp/skykin_inbound.lua.SHORT-BAD-$(date +%Y%m%d-%H%M%S) || true

docker cp /tmp/skykin_inbound.lua.full \\
  skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua

for d in /opt/skykin/docker/freeswitch/scripts /opt/skykin/app/docker/freeswitch/scripts /opt/skykin/fs-live; do
  if [ -d "$d" ]; then cp -a /tmp/skykin_inbound.lua.full "$d/skykin_inbound.lua"; fi
done

docker exec skykin-freeswitch touch /etc/freeswitch/scripts/skykin_biz_hours_off

echo '==== VERIFY ===='
docker exec skykin-freeswitch grep -n 'ALWAYS WebRTC\\|outside_business_hours\\|retry once\\|hangup_after_bridge\\|media_webrtc=true\\|biz_hours_off' \\
  /etc/freeswitch/scripts/skykin_inbound.lua | head -25
docker exec skykin-freeswitch ls -la /etc/freeswitch/scripts/skykin_inbound.lua /etc/freeswitch/scripts/skykin_biz_hours_off
echo 'DONE — full lua restored; after-hours bypassed for testing.'
echo 'Restore hours later: docker exec skykin-freeswitch rm -f /etc/freeswitch/scripts/skykin_biz_hours_off'
"""

out = root / "scripts/restore_full_inbound_ah.sh"
out.write_text(script.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
print("wrote", out, "size", out.stat().st_size, "lua_lines", lua.count(b"\n") + 1)
