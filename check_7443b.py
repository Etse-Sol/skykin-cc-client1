import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=25):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== curl 7443 local ====")
print(run("timeout 4 curl -skvI https://127.0.0.1:7443/ 2>&1 | tail -25"))

print("==== listen ====")
print(run("ss -lnt | grep -E '7443|5066|5060' || netstat -lnt | grep -E '7443|5066'"))

print("==== contacts ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"))

c.close()
