import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=30):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== sofia status ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | grep -iE 'BIND|WSS|WS-|FAILED|RUNNING'"))

print("==== 7443 / wss.pem ====")
print(run("docker exec skykin-freeswitch sh -c 'ss -lnt; echo ---; ls -l /etc/freeswitch/tls; openssl x509 -in /etc/freeswitch/tls/wss.pem -noout -subject -dates 2>&1 | head'"))

print("==== restart errors ====")
print(run("docker exec skykin-freeswitch sh -c \"grep -aE 'wss.pem|WSS|7443|tls|internal' /var/log/freeswitch/freeswitch.log | tail -30\""))

print("==== regs ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg' | grep -E 'User:|Total'"))
c.close()
