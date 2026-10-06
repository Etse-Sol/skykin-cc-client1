import base64
import urllib.request
from pathlib import Path

root = Path(r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard")
files = ["skykin_config.php", "supervisor.php", "index.php", "data.php"]
parts = []
for f in files:
    b64 = base64.b64encode((root / f).read_bytes()).decode("ascii")
    parts.append((f, b64))
    print(f, len(b64))

lines = ["#!/bin/bash", "set -euo pipefail", "WEB=/var/www/fusionpbx/app/agent_dashboard"]
for f, b64 in parts:
    var = "B64_" + f.replace(".", "_")
    lines.append(f"{var}='{b64}'")
    lines.append(f'echo "${{{var}}}" | base64 -d > /tmp/{f}')
    lines.append(f"docker cp /tmp/{f} skykin-web:$WEB/{f}")

lines.append("docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true")
lines.append(
    r"""docker exec skykin-web php -r '
require "/var/www/fusionpbx/app/agent_dashboard/skykin_config.php";
$ivr=["direction"=>"inbound","billsec"=>40,"waitsec"=>0,"last_arg"=>"","cc_agent_bridged"=>"","bridge_uuid"=>""];
$ok=["direction"=>"inbound","billsec"=>90,"waitsec"=>20,"last_arg"=>"user/203@ahununu","cc_agent_bridged"=>"","bridge_uuid"=>""];
$cc=["direction"=>"inbound","billsec"=>60,"waitsec"=>10,"last_arg"=>"","cc_agent_bridged"=>"/203@ahununu","bridge_uuid"=>"abc"];
echo skykin_cdr_result_label($ivr)," ",skykin_cdr_result_label($ok)," ",skykin_cdr_result_label($cc),"\n";
'"""
)
lines.append("echo DONE")

out = Path(r"C:\Users\hp\skykin-fusionpbx\deploy_cdr_answered_fix.sh")
out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
data = out.read_bytes()
boundary = "----SkykinAnsFix"
body = (
    f"--{boundary}\r\n".encode()
    + b'Content-Disposition: form-data; name="reqtype"\r\n\r\nfileupload\r\n'
    + f"--{boundary}\r\n".encode()
    + b'Content-Disposition: form-data; name="time"\r\n\r\n72h\r\n'
    + f"--{boundary}\r\n".encode()
    + b'Content-Disposition: form-data; name="fileToUpload"; filename="deploy_cdr_answered_fix.sh"\r\n'
    + b"Content-Type: application/x-sh\r\n\r\n"
    + data
    + f"\r\n--{boundary}--\r\n".encode()
)
req = urllib.request.Request(
    "https://litterbox.catbox.moe/resources/internals/api.php",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "curl/8.5"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=180) as r:
    print("URL", r.read().decode().strip())
