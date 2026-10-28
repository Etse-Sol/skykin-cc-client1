"""Build a paste-only deploy script for the main PBX host (gitignored)."""
from __future__ import annotations

import base64
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_PASTE_PRO_DEPLOY.sh"
PHP_FILES = [
    "app/agent_dashboard/skyconnect_ops.php",
    "app/agent_dashboard/evaluation.php",
    "app/agent_dashboard/crm.php",
    "app/agent_dashboard/skykin_ai.php",
    "app/agent_dashboard/skykin_config.php",
    "app/agent_dashboard/reports.php",
]

FIX_NGINX = r'''
import re, sys
path, gw = sys.argv[1], sys.argv[2]
conf = open(path, encoding="utf-8", errors="replace").read()
for loc in ("/asr", "/v1/evaluate", "/v1/transcribe", "/v1/audio/transcriptions"):
    conf = re.sub(
        r"\n[ \t]*location " + re.escape(loc) + r" \{.*?\n[ \t]*\}\n?",
        "\n",
        conf,
        flags=re.S,
    )
snip = f"""
    # SkyKin AI (host :8100 via docker gateway)
    location /asr {{
        proxy_pass http://{gw}:8100;
        proxy_http_version 1.1;
        client_max_body_size 25m;
        proxy_read_timeout 180s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
    location /v1/evaluate {{
        proxy_pass http://{gw}:8100;
        proxy_http_version 1.1;
        client_max_body_size 25m;
        proxy_read_timeout 180s;
        proxy_set_header Host $host;
    }}
    location /v1/transcribe {{
        proxy_pass http://{gw}:8100;
        proxy_http_version 1.1;
        client_max_body_size 25m;
        proxy_read_timeout 180s;
        proxy_set_header Host $host;
    }}
    location /v1/audio/transcriptions {{
        proxy_pass http://{gw}:8100;
        proxy_http_version 1.1;
        client_max_body_size 25m;
        proxy_read_timeout 180s;
        proxy_set_header Host $host;
    }}
"""

def blocks(text):
    out, i = [], 0
    while True:
        m = re.search(r"server\s*\{", text[i:], flags=re.I)
        if not m:
            break
        start = i + m.start()
        brace = i + m.end() - 1
        depth = 0
        for j in range(brace, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    out.append((start, j + 1, text[start : j + 1]))
                    i = j + 1
                    break
        else:
            break
    return out

bs = blocks(conf)
if not bs:
    raise SystemExit("no nginx server blocks")
bs.sort(key=lambda b: (("443" in b[2]) * 10 + ("ssl" in b[2].lower()) * 5), reverse=True)
start, end, body = bs[0]
m = re.match(r"server\s*\{", body, flags=re.I)
body = body[: m.end()] + "\n" + snip + body[m.end() :]
conf = conf[:start] + body + conf[end:]
open(path, "w", encoding="utf-8").write(conf)
print("nginx AI locations inserted")
'''


def add_dir(tar: tarfile.TarFile, src: Path, arc: str) -> None:
    for p in sorted(src.rglob("*")):
        if p.is_file():
            tar.add(p, arcname=f"{arc}/{p.relative_to(src).as_posix()}")


def add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def main() -> None:
    dist = ROOT / "skyconnect" / "dist"
    if not (dist / "index.html").is_file():
        raise SystemExit("Run npm run build in skyconnect/ first")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        add_dir(tar, dist, "ui")
        for rel in PHP_FILES:
            p = ROOT / rel
            if not p.is_file():
                raise SystemExit(f"missing {rel}")
            tar.add(p, arcname=f"php/{p.name}")
        add_bytes(tar, "fix_nginx.py", FIX_NGINX.encode("utf-8"))
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    script = """#!/bin/sh
# SkyConnect professional pack — paste on the PBX host as root.
# Does not change inbound.lua / early-answer.
set -e
STAMP=$(date +%Y%m%d%H%M%S)
DASH=/opt/skykin/skykin-cc-client1/app/agent_dashboard
WEB_DASH=/var/www/fusionpbx/app/agent_dashboard
CONF=/etc/nginx/sites-available/skykin.conf
python3 - <<'PY'
import base64, pathlib
pathlib.Path("/tmp/sc-pro.tgz").write_bytes(base64.b64decode(""" + '"' + b64 + '"' + """))
print("wrote /tmp/sc-pro.tgz", pathlib.Path("/tmp/sc-pro.tgz").stat().st_size)
PY
rm -rf /tmp/sc-pro
mkdir -p /tmp/sc-pro
tar -xzf /tmp/sc-pro.tgz -C /tmp/sc-pro
test -f /tmp/sc-pro/ui/index.html
test -f /tmp/sc-pro/php/skyconnect_ops.php

echo "=== host tree ==="
if [ -d "$DASH" ]; then
  mkdir -p "$DASH/skyconnect"
  rm -rf "$DASH/skyconnect"/*
  cp -a /tmp/sc-pro/ui/. "$DASH/skyconnect/"
  cp -a /tmp/sc-pro/php/. "$DASH/"
fi

echo "=== skykin-web ==="
if docker ps --format '{{.Names}}' | grep -qx skykin-web; then
  docker exec skykin-web mkdir -p "$WEB_DASH/skyconnect"
  docker cp /tmp/sc-pro/ui/. skykin-web:"$WEB_DASH/skyconnect/"
  docker cp /tmp/sc-pro/php/. skykin-web:"$WEB_DASH/"
  GW=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.Gateway}} {{end}}' skykin-web | awk '{print $1}')
  [ -z "$GW" ] && GW=172.18.0.1
  echo "GW=$GW"
  TMP=/tmp/skykin.conf.pro.$STAMP
  docker cp "skykin-web:$CONF" "$TMP"
  python3 /tmp/sc-pro/fix_nginx.py "$TMP" "$GW"
  docker exec skykin-web cp -a "$CONF" "$CONF.bak-pro-$STAMP" || true
  docker cp "$TMP" "skykin-web:$CONF"
  docker exec skykin-web nginx -t
  docker exec skykin-web nginx -s reload
  mkdir -p /etc/skykin
  if [ ! -f /etc/skykin/ai.env ]; then
    printf 'SKYKIN_AI=on\\nSKYKIN_AI_MODE=skykin\\nSKYKIN_AI_BASE_URL=http://%s:8100\\n' "$GW" > /etc/skykin/ai.env
    echo "wrote /etc/skykin/ai.env"
  fi
  docker exec skykin-web mkdir -p /etc/skykin || true
  docker cp /etc/skykin/ai.env skykin-web:/etc/skykin/ai.env || true
else
  echo "skykin-web not running — host files only"
fi

echo "=== :8100 ==="
if command -v ss >/dev/null 2>&1; then
  ss -lntp | grep ':8100' || echo "NOTHING on :8100 — start SkyKin AI with SKYKIN_AI_HOST=0.0.0.0"
fi
echo "DONE $STAMP"
"""
    OUT.write_text(script.replace("\r\n", "\n"), encoding="utf-8")
    print("wrote", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
