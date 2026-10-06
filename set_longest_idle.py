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
python3 - <<'PY'
from pathlib import Path
p = Path("/root/skykin-fs-etc/autoload_configs/callcenter.conf.xml")
t = p.read_text()
t2 = t.replace(
    '<param name="strategy" value="ring-all"/>',
    '<param name="strategy" value="longest-idle-agent"/>',
)
if t2 == t:
    raise SystemExit("strategy line not found or already longest-idle")
p.write_text(t2)
print("xml strategy -> longest-idle-agent")
PY
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c \
  "UPDATE v_call_center_queues SET queue_strategy = 'longest-idle-agent' WHERE queue_extension = '8000';"
docker exec skykin-freeswitch fs_cli -x reloadxml
docker exec skykin-freeswitch fs_cli -x "callcenter_config queue reload 8000@client1.skykin.local"
# Keep 101 out so longest-idle does not offer a dead MicroSIP first
WEB='[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,rtp_advertise_ip=196.189.236.140,include_external_ip=true]'
docker exec skykin-freeswitch fs_cli -x \
  "callcenter_config agent set status 64c5f323-cd40-48ef-a97f-22d546be8b57 'Logged Out'"
docker exec skykin-freeswitch fs_cli -x \
  "callcenter_config agent set contact 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e '${WEB}user/102@client1.skykin.local'"
docker exec skykin-freeswitch fs_cli -x \
  "callcenter_config agent set contact cd794b4f-f54e-4110-ba5d-537a034c243c '${WEB}user/103@client1.skykin.local'"
docker exec skykin-freeswitch fs_cli -x \
  "callcenter_config agent set max_no_answer 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e 999"
docker exec skykin-freeswitch fs_cli -x \
  "callcenter_config agent set max_no_answer cd794b4f-f54e-4110-ba5d-537a034c243c 999"
echo '==== queue ===='
docker exec skykin-freeswitch fs_cli -x "callcenter_config queue list" | awk -F'|' 'NR<=2{print $1,$2}'
echo '==== agents ===='
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent list" | cut -d'|' -f1,5,6,7
"""
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
