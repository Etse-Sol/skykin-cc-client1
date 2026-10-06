import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=50):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


print("==== certs now ====")
print(run("docker exec skykin-web ls -l /etc/ssl/skykin/ 2>/dev/null; docker exec skykin-freeswitch ls -l /etc/freeswitch/tls /usr/share/freeswitch/tls 2>/dev/null"))
print(run("docker exec skykin-freeswitch grep -n 'tls-cert\\|wss-cert\\|certs_dir\\|tls-bind' /etc/freeswitch/sip_profiles/internal.xml /etc/freeswitch/vars.xml | head -30"))
print(run("ss -lnt | grep 7443; echo ---; ss -tnp | grep 7443 | head"))

c.close()
