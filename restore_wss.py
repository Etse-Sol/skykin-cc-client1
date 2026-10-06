import sys
import time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print(run(r"""
docker exec skykin-web sh -c '
f=/etc/nginx/sites-enabled/skykin.conf
sed -i "s#proxy_pass http://172.22.0.1:18081;#proxy_pass https://172.22.0.1:7443;#" "$f"
grep -n proxy_pass "$f"
nginx -t && nginx -s reload
'
"""))
print(run("systemctl stop skykin-ws-sip; systemctl disable skykin-ws-sip"))
print("waiting for regs after agents retry...")
for i in range(8):
    time.sleep(3)
    regs = run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'")
    users = [ln for ln in regs.splitlines() if ln.strip().startswith("User:")]
    print(f"  {i}: {users}")
    if users:
        print(regs)
        break
c.close()
