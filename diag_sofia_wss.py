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


print("==== profile internal key params ====")
print(run("docker exec skykin-freeswitch grep -n 'sip-force-contact\\|NDLB\\|aggressive-nat\\|apply-nat\\|rfc-5626\\|wss-binding\\|ext-rtp' /etc/freeswitch/sip_profiles/internal.xml"))

print("==== public 7443 from host ====")
print(run("timeout 3 curl -skI --connect-timeout 2 https://196.189.236.140:7443/ 2>&1 | tail -15"))
print(run("timeout 3 curl -skI --connect-timeout 2 https://10.0.0.93:7443/ 2>&1 | tail -10"))

print("==== iptables 7443 ====")
print(run("iptables -L INPUT -n | grep 7443; iptables -L ufw-user-input -n 2>/dev/null | grep 7443"))

c.close()
