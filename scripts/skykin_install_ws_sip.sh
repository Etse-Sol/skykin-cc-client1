#!/bin/sh
# ws-sip gateway: browser WSS -> FreeSWITCH UDP SIP on 127.0.0.1:5060.
# Without this, nginx /wss/ -> 7443 leaves fs_path on the registration contact;
# agent-to-agent bridge then tries a new WSS to nginx's ephemeral port -> 503.
#
# Run on ecs-testbed as root from repo root:
#   bash scripts/skykin_install_ws_sip.sh
set -eu

REPO="${REPO:-/opt/skykin/skykin-cc-client1}"
PY="$REPO/docker/ws-sip/skykin_ws_sip.py"
UNIT=/etc/systemd/system/skykin-ws-sip.service

if [ ! -f "$PY" ]; then
	echo "missing $PY"
	exit 1
fi

if ! python3 -c "import websockets" 2>/dev/null; then
	apt-get update
	apt-get install -y python3-websockets 2>/dev/null || pip3 install --break-system-packages websockets
fi

cat > "$UNIT" <<EOF
[Unit]
Description=SkyKin WS-SIP UDP gateway (agent softphone)
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
Environment=SKYKIN_FS_SIP_HOST=127.0.0.1
Environment=SKYKIN_FS_SIP_PORT=5060
Environment=SKYKIN_FS_UDP_BIND=127.0.0.1
Environment=SKYKIN_WS_SIP_HOST=0.0.0.0
Environment=SKYKIN_WS_SIP_PORT=18081
ExecStart=/usr/bin/python3 $PY
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable skykin-ws-sip
systemctl restart skykin-ws-sip
sleep 1
systemctl is-active skykin-ws-sip
ss -lntp | grep 18081 || netstat -lntp | grep 18081 || true
echo "ws-sip OK on :18081 — point FREESWITCH_WS_UPSTREAM=172.18.0.1:18081 (http)"
