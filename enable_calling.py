import sys
import time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOCAL = r"C:\Users\hp\skykin-fusionpbx\skykin_ws_sip.py"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=60):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


sftp = c.open_sftp()
with open(LOCAL, "rb") as f:
    data = f.read()
with sftp.file("/etc/skykin/skykin_ws_sip.py", "wb") as rf:
    rf.write(data)
sftp.close()
print("uploaded", len(data))

print(run(r"""
cat > /etc/systemd/system/skykin-ws-sip.service <<'EOF'
[Unit]
Description=SkyKin WS-to-SIP gateway
After=network.target docker.service

[Service]
ExecStart=/usr/bin/python3 /etc/skykin/skykin_ws_sip.py
Restart=always
RestartSec=2
Environment=SKYKIN_FS_SIP_HOST=10.0.0.93
Environment=SKYKIN_FS_SIP_PORT=5060
Environment=SKYKIN_FS_UDP_BIND=10.0.0.93
Environment=SKYKIN_WS_SIP_HOST=0.0.0.0
Environment=SKYKIN_WS_SIP_PORT=18081

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now skykin-ws-sip
sleep 1
systemctl restart skykin-ws-sip
sleep 1
systemctl is-active skykin-ws-sip
"""))

print("==== probe REGISTER via gateway ====")
print(run(r"""python3 - <<'PY'
import asyncio
import websockets

REG = (
    "REGISTER sip:client1.skykin.local SIP/2.0\r\n"
    "Via: SIP/2.0/WSS abc.invalid;branch=z9hG4bKgwtest1\r\n"
    "From: <sip:102@client1.skykin.local>;tag=gwtest\r\n"
    "To: <sip:102@client1.skykin.local>\r\n"
    "Call-ID: gw-test-001\r\n"
    "CSeq: 1 REGISTER\r\n"
    "Contact: <sip:gwtest@abc.invalid;transport=wss>\r\n"
    "Expires: 60\r\n"
    "Content-Length: 0\r\n"
    "\r\n"
)

async def main():
    async with websockets.connect("ws://127.0.0.1:18081", subprotocols=["sip"]) as ws:
        await ws.send(REG)
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print("GOT", msg.split("\r\n", 1)[0])
            print(msg[:400])
        except Exception as e:
            print("NO_REPLY", type(e).__name__, e)

asyncio.run(main())
PY"""))

print("==== gateway log ====")
print(run("journalctl -u skykin-ws-sip -n 15 --no-pager"))
c.close()
