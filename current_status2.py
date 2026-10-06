import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=45):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== SIP.xml ====")
print(run("docker exec skykin-freeswitch cat /etc/freeswitch/sip_profiles/external/SIP.xml 2>&1 | sed 's/^/  /'"))

print("==== outbound extensions in domain dialplan ====")
print(run("docker exec skykin-freeswitch sh -c 'grep -n \"extension name\\|sofia/gateway\" /etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml' 2>&1 | sed 's/^/  /'"))

print("==== public dialplan files ====")
print(run("docker exec skykin-freeswitch ls -l /etc/freeswitch/dialplan/public/ 2>&1 | sed 's/^/  /'"))

print("==== 5080 NAT / published ports ====")
print(run("iptables -t nat -S | grep -E '5080|16384' | sed 's/^/  /' || true"))
print(run("docker port skykin-freeswitch 2>&1 | sed 's/^/  /'"))

print("==== sofia profile external ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status' 2>&1 | sed 's/^/  /'"))

print("==== container started / recreate ====")
print(run("docker inspect -f '{{.State.StartedAt}} recreate={{.RestartCount}}' skykin-freeswitch 2>&1 | sed 's/^/  /'"))

c.close()
