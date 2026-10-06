import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
# 101 and 103 are not SIP-registered; offering them first makes inbound die
# before 102 rings. Park them until they sign in.
for uid, label in [
    ("64c5f323-cd40-48ef-a97f-22d546be8b57", "101"),
    ("cd794b4f-f54e-4110-ba5d-537a034c243c", "103"),
]:
    _, o, e = c.exec_command(
        f"docker exec skykin-freeswitch fs_cli -x \"callcenter_config agent set status {uid} 'Logged Out'\""
    )
    print(label, o.read().decode(), e.read().decode())
_, o, e = c.exec_command(
    "docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | "
    "awk -F'|' 'NR==1||NR>1{print $1,$6,$7}'"
)
print(o.read().decode())
c.close()
