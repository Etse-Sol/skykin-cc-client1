import sys
import time
import ssl
import socket
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal restart'"))
print("waiting for 127.0.0.1 regs...")
for i in range(12):
    time.sleep(3)
    regs = run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'")
    print(f"--- {i} ---")
    for ln in regs.splitlines():
        if any(x in ln for x in ("User:", "Contact:", "IP:", "Status:", "Agent:")):
            print(ln)
    if "127.0.0.1" in regs:
        break

print("==== gateway log ====")
print(run("journalctl -u skykin-ws-sip -n 25 --no-pager"))
print("==== nginx errors ====")
print(run("docker exec skykin-web sh -c 'tail -8 /var/log/nginx/error.log'"))
c.close()

print("==== remote /wss/ ====")
try:
    req = (
        "GET /wss/ HTTP/1.1\r\nHost: 196.189.236.140:8088\r\nUpgrade: websocket\r\n"
        "Connection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        "Sec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: sip\r\n\r\n"
    ).encode()
    ctx = ssl._create_unverified_context()
    s = socket.create_connection(("196.189.236.140", 8088), 8)
    ss = ctx.wrap_socket(s, server_hostname="196.189.236.140")
    ss.sendall(req)
    ss.settimeout(8)
    print(ss.recv(400).decode("latin1", "replace"))
    ss.close()
except Exception as e:
    print("fail", type(e).__name__, e)
