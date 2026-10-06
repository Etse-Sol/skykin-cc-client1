import sys
import time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=60):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("restart nginx workers to drop old WSS (keep container config)...")
print(run("docker exec skykin-web sh -c 'grep proxy_pass /etc/nginx/sites-enabled/skykin.conf; nginx -s quit; sleep 1; nginx; sleep 1; nginx -t'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal flush_inbound_reg'"))

print("waiting for gateway regs...")
for i in range(15):
    time.sleep(3)
    regs = run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'")
    print(f"--- {i} ---")
    for ln in regs.splitlines():
        if any(x in ln for x in ("User:", "Contact:", "IP:", "Status:")):
            print(ln)
    if "127.0.0.1" in regs:
        print("SUCCESS")
        print(regs)
        break

print("==== gateway ====")
print(run("journalctl -u skykin-ws-sip -n 20 --no-pager"))
c.close()
