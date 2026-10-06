import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    "ss -lntp | grep -E ':8080|:8088|:18081|:7443'",
    "docker ps --format '{{.Names}} {{.Ports}}' | head -20",
    "docker exec skykin-web nginx -T 2>/dev/null | grep -E 'listen |proxy_pass|server_name' | head -40",
    "ufw status | grep -E '8080|8088'",
]
for cmd in cmds:
    print("====", cmd)
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
