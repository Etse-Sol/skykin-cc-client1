import sys
import time
import socket
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HOST = "196.189.236.140"
LOCAL_PHP = r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php"
REMOTE_PHP = [
    "/opt/call-center-deployement/call-center/app/agent_dashboard/index.php",
    "/var/www/fusionpbx/app/agent_dashboard/index.php",
]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=45):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


sftp = c.open_sftp()
with open(LOCAL_PHP, "rb") as f:
    data = f.read()
for path in REMOTE_PHP:
    try:
        with sftp.file(path, "wb") as rf:
            rf.write(data)
        print("uploaded", path, len(data))
    except Exception as e:
        print("skip", path, e)
sftp.close()

print(run("php -l /opt/call-center-deployement/call-center/app/agent_dashboard/index.php"))
print(run(r"""
f=/root/skykin-fs-etc/sip_profiles/internal.xml
# live bind-mount
if [ ! -f "$f" ]; then f=/etc/freeswitch/sip_profiles/internal.xml; fi
docker exec skykin-freeswitch sh -c '
f=/etc/freeswitch/sip_profiles/internal.xml
if grep -q "name=\"disable-tcp\"" "$f"; then
  sed -i "s#<!--[[:space:]]*<param name=\"disable-tcp\"[^>]*/>[[:space:]]*-->#<param name=\"disable-tcp\" value=\"true\"/>#" "$f"
  sed -i "s#<param name=\"disable-tcp\" value=\"[^\"]*\"/>#<param name=\"disable-tcp\" value=\"true\"/>#" "$f"
else
  sed -i "s#</settings>#    <param name=\"disable-tcp\" value=\"true\"/>\n  </settings>#" "$f"
fi
sed -i "s#<param name=\"wss-binding\".*#<param name=\"wss-binding\" value=\"0.0.0.0:5060\"/>#" "$f"
grep -n "disable-tcp\\|wss-binding\\|ws-binding\\|sip-port" "$f"
'
"""))

print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal restart'"))
print("waiting for profile...")
for i in range(8):
    time.sleep(2)
    st = run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | grep -E 'BIND-URL|WSS-BIND|WS-BIND|failed|UP'")
    print(f"  {i}: {st.strip()}")
    if "5060" in st and "wss" in st.lower():
        break

print("==== sofia status (bind) ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | head -25"))
print("==== host 5060 ====")
print(run("ss -lntp | grep -E ':5060|:7443' || true"))
c.close()

print("==== TLS 5060 from this PC ====")
s = socket.socket()
s.settimeout(5)
try:
    s.connect((HOST, 5060))
    print("TCP 5060 OPEN")
    s.close()
except Exception as e:
    print("TCP 5060", e)
