import sys
import time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOCAL = r"C:\Users\hp\skykin-fusionpbx\skykin_ws_sip.py"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=90):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


sftp = c.open_sftp()
sftp.mkdir("/etc/skykin") if False else None
try:
    sftp.stat("/etc/skykin")
except OSError:
    run("mkdir -p /etc/skykin")
with open(LOCAL, "rb") as f:
    data = f.read()
with sftp.file("/etc/skykin/skykin_ws_sip.py", "wb") as rf:
    rf.write(data)
sftp.close()
print("uploaded gateway", len(data))

print(run("python3 -m pip install -q websockets 2>/dev/null || pip3 install -q websockets"))

print(run(r"""
cat > /etc/systemd/system/skykin-ws-sip.service <<'EOF'
[Unit]
Description=SkyKin WS-to-SIP gateway
After=network.target docker.service

[Service]
ExecStart=/usr/bin/python3 /etc/skykin/skykin_ws_sip.py
Restart=always
RestartSec=2
Environment=SKYKIN_FS_SIP_HOST=127.0.0.1
Environment=SKYKIN_FS_SIP_PORT=5060
Environment=SKYKIN_WS_SIP_HOST=0.0.0.0
Environment=SKYKIN_WS_SIP_PORT=8081

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now skykin-ws-sip
sleep 1
systemctl is-active skykin-ws-sip
ss -lntp | grep 8081 || true
"""))

print("==== nginx to gateway ====")
print(run(r"""
docker exec skykin-web sh -c '
f=/etc/nginx/sites-enabled/skykin.conf
sed -i "s#proxy_pass https://172.22.0.1:7443;#proxy_pass http://172.22.0.1:8081;#" "$f"
sed -i "s#proxy_pass https://127.0.0.1:7443;#proxy_pass http://172.22.0.1:8081;#" "$f"
grep -n proxy_pass "$f"
nginx -t && nginx -s reload
'
ufw allow from 172.16.0.0/12 to any port 8081 proto tcp comment skykin-ws-sip >/dev/null
"""))

print("==== lua + webrtc ua ====")
print(run(r"""
docker exec skykin-freeswitch sh -c 'cat > /usr/share/freeswitch/scripts/skykin_dest.lua << "LUA"
local api = freeswitch.API()
local user = argv[1] or ""
local domain = argv[2] or "client1.skykin.local"
local contact = api:execute("sofia_contact", "*/" .. user .. "@" .. domain) or ""
if contact == "" or contact:find("error") or contact:find("not found") then
  stream:write("error/user_not_registered")
  return
end
if contact:find("127.0.0.1") or contact:find("transport=ws") or contact:find(".invalid") then
  stream:write("{media_webrtc=true,rtp_secure_media=optional,rtp_advertise_ip=196.189.236.140,include_external_ip=true}" .. contact)
else
  stream:write("{rtp_secure_media=optional}" .. contact)
end
LUA
cat > /etc/freeswitch/dialplan/default/00_skykin_webrtc_ua.xml << "XML"
<include>
  <extension name="skykin_webrtc_ua" continue="true">
    <condition field="${sip_user_agent}" expression="SIP\.js">
      <action application="set" data="media_webrtc=true"/>
      <action application="set" data="rtp_secure_media=optional"/>
      <action application="set" data="rtp_advertise_ip=196.189.236.140"/>
      <action application="set" data="include_external_ip=true"/>
    </condition>
  </extension>
</include>
XML
'
docker exec skykin-freeswitch fs_cli -x 'reloadxml'
docker exec skykin-freeswitch fs_cli -x 'sofia profile internal restart'
"""))

print("waiting for agents to reconnect via gateway...")
for i in range(10):
    time.sleep(3)
    regs = run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'")
    users = [ln for ln in regs.splitlines() if "User:" in ln or "Contact:" in ln or "IP:" in ln]
    print(f"--- {i} ---")
    print("\n".join(users) if users else regs[:400])
    if "127.0.0.1" in regs:
        print(regs)
        break

print("==== gateway log ====")
print(run("journalctl -u skykin-ws-sip -n 30 --no-pager"))
c.close()
