# skykin-cc-client1

Client1 call-center tree for **ecs-testbed** (`196.189.237.77`).

- No Ahununu dialplan / SIP8035–8039 overlay
- Keeps client1 + SIP / SIP2 / SIP757–759 path
- Live Ahununu stays on **ecs-cc** via `skykin-fusionpbx` — do not deploy this repo there

## Deploy (ecs-testbed only)

```bash
# wipe old clone
cd /opt/skykin/skykin-fusionpbx 2>/dev/null && \
  docker compose -f docker-compose.ecs-cc.yml --env-file .env down -v || true
rm -rf /opt/skykin/skykin-fusionpbx /opt/skykin/skykin-cc-client1
mkdir -p /opt/skykin/fs-config
```

From your PC:

```powershell
scp -r C:\Users\hp\skykin-cc-client1 root@196.189.237.77:/opt/skykin/
```

On server:

```bash
cd /opt/skykin/skykin-cc-client1
cp .env.client1-testbed.example .env
# edit passwords in .env
docker compose -f docker-compose.ecs-cc.yml --env-file .env up --build -d
docker ps
docker logs skykin-freeswitch --tail 40
```

Expect log line: `client1-only: ahununu dialplan omitted` and FreeSWITCH **Up**.
