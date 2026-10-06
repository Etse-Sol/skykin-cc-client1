import socket
import sys
import time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "196.189.236.140"
ports = [80, 443, 5060, 5066, 5080, 7443, 8088, 8443, 9443]


def probe(port, timeout=3):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((HOST, port))
        s.close()
        return "OPEN"
    except Exception as e:
        return type(e).__name__


print("==== TCP from this PC ====")
for p in ports:
    print(f"  {p}: {probe(p)}")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== host listeners ====")
print(run("ss -lntup | grep -E ':80 |:443 |:5060 |:5066 |:5080 |:7443 |:8088 |:8443 |:9443 ' || netstat -lntup 2>/dev/null | grep -E ':80 |:443 |:5066 |:7443 |:8088 '"))

print("==== nat params ====")
print(run(r"""docker exec skykin-freeswitch sh -c "grep -nE 'nat|force-contact|5626|ws-binding|wss-binding|aggressive|NDLB|local-network' /etc/freeswitch/sip_profiles/internal.xml | head -40" """))

print("==== webrtc dialplan ====")
print(run("docker exec skykin-freeswitch sh -c 'echo === default ===; cat /etc/freeswitch/dialplan/default/00_webrtc_local.xml; echo === lua ===; cat /usr/share/freeswitch/scripts/skykin_dest.lua 2>/dev/null || echo NO_LUA'"))

print("==== last agent call ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'Processing 10[123].*10[123]|TEMPORARY_FAILURE|sending invite call-id|hangup complete' /var/log/freeswitch/freeswitch.log | tail -25\""))

print("==== regs ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))

print("==== siptrace on, wait, sample REGISTER ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal siptrace on'"))
print("waiting 8s for a re-register...")
time.sleep(8)
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'REGISTER sip:|Contact:|\\\\+sip.instance|reg-id|;ob' /var/log/freeswitch/freeswitch.log | tail -40\""))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal siptrace off'"))
c.close()
