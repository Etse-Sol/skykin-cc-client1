import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=45):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


# Keep 103/104 in .env and switch the trunk to IMS register.
run(r"""python3 - <<'PY'
from pathlib import Path
p = Path("/opt/call-center-deployement/call-center/.env")
t = p.read_text()
changed = False
if "103:22223333" not in t:
    t = t.replace(
        "FS_DIRECTORY_USERS=100:11112222,101:1234567890,102:0987654321",
        "FS_DIRECTORY_USERS=100:11112222,101:1234567890,102:0987654321,103:22223333",
    )
    changed = True
repls = {
    "FS_OUTBOUND_REGISTER=false": "FS_OUTBOUND_REGISTER=true",
}
for a, b in repls.items():
    if a in t:
        t = t.replace(a, b)
        changed = True
extras = {
    "FS_OUTBOUND_REALM": "ims.ethiotelecom.com",
    "FS_OUTBOUND_AUTH_USERNAME": "+251111138755@ims.ethiotelecom.com",
    "FS_OUTBOUND_FROM_DOMAIN": "ims.ethiotelecom.com",
    "FS_OUTBOUND_REGISTER_PROXY": "10.208.233.134",
    "FS_LAN_RTP_IP": "10.0.0.93",
    "FS_INBOUND_DID_REGEX": r"^\\+?(?:251)?0?11113875[59]$",
}
for k, v in extras.items():
    if f"{k}=" not in t:
        t = t.rstrip() + f"\n{k}={v}\n"
        changed = True
if changed:
    p.write_text(t)
    print("updated server .env")
else:
    print("server .env already current")
PY""")

print("==== gateway ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status gateway SIP' | grep -E 'Name|State|Status|Username|Realm|Contact'"))

print("==== user exists ====")
for ext in ("101", "102", "103", "104"):
    print(f"  {ext}:", run(f"docker exec skykin-freeswitch fs_cli -x 'user_exists id {ext} client1.skykin.local'").strip())

print("==== registrations ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg' | grep -E 'User:|Status:|Total'"))

print("==== local + outbound rules ====")
print(run("docker exec skykin-freeswitch grep -n 'skykin_outbound\\|webrtc_local\\|1\\\\d' /etc/freeswitch/dialplan/default/00_webrtc_local.xml /etc/freeswitch/dialplan/default/00_skykin.xml | head -30"))

c.close()
