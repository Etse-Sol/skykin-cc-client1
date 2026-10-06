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


print("==== install dashboard cert as FS wss.pem ====")
print(run("""
docker cp skykin-web:/etc/ssl/skykin/fullchain.pem /tmp/skykin-fullchain.pem
docker cp skykin-web:/etc/ssl/skykin/privkey.pem /tmp/skykin-privkey.pem
cat /tmp/skykin-fullchain.pem /tmp/skykin-privkey.pem > /tmp/wss.pem
docker cp /tmp/wss.pem skykin-freeswitch:/etc/freeswitch/tls/wss.pem
docker exec skykin-freeswitch ls -l /etc/freeswitch/tls/wss.pem
"""))

print("==== open 7443 ====")
print(run("ufw allow 7443/tcp comment 'skykin-wss-direct' ; ufw status | grep 7443"))

print("==== point dashboard at :7443 ====")
print(run(r"""
docker exec skykin-web sh -c "
sed -i \"s#/wss/';#':7443';#\" /var/www/fusionpbx/app/agent_dashboard/index.php
sed -i \"s#pagePort + '/wss/'#:7443#g\" /var/www/fusionpbx/app/agent_dashboard/index.php
grep -n '7443\\|/wss/' /var/www/fusionpbx/app/agent_dashboard/index.php | head -20
"
"""))

print(run("docker exec skykin-freeswitch fs_cli -x 'sofia profile internal restart'"))
print(run("sleep 2; timeout 3 curl -skI https://127.0.0.1:7443/ | head -8; echo ---; ss -lnt | grep 7443 || docker exec skykin-freeswitch ss -lnt | grep 7443"))
print("DONE")
c.close()
