import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    username="root",
    password="Pass@1234",
    timeout=25,
    allow_agent=False,
    look_for_keys=False,
)
cmds = r"""
# 101 MicroSIP is stale / not registered — stop offering it first
docker exec skykin-freeswitch fs_cli -x \
  "callcenter_config agent set status 64c5f323-cd40-48ef-a97f-22d546be8b57 'Logged Out'"

# Ring every available dashboard agent, not just longest-idle 101
python3 - <<'PY'
from pathlib import Path
p = Path("/root/skykin-fs-etc/autoload_configs/callcenter.conf.xml")
t = p.read_text()
t2 = t.replace(
    '<param name="strategy" value="longest-idle-agent"/>',
    '<param name="strategy" value="ring-all"/>',
)
if t2 != t:
    p.write_text(t2)
    print("strategy -> ring-all")
else:
    print("strategy line missing or already ring-all")
    print(t)
PY
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c \
  "UPDATE v_call_center_queues SET queue_strategy = 'ring-all' WHERE queue_extension = '8000';" \
  2>/dev/null || true
docker exec skykin-freeswitch fs_cli -x reloadxml
docker exec skykin-freeswitch fs_cli -x "callcenter_config queue reload 8000@client1.skykin.local"
echo '==== agents ===='
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent list" | cut -d'|' -f1,6,7
echo '==== queue ===='
docker exec skykin-freeswitch fs_cli -x "callcenter_config queue list" | head -3
"""
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
