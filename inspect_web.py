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


print(run("docker inspect skykin-web --format '{{json .HostConfig.PortBindings}} {{json .HostConfig.Binds}} {{.HostConfig.NetworkMode}}'"))
print("==== ports ====")
print(run("docker port skykin-web"))
print("==== certs ====")
print(run("docker exec skykin-web ls -l /etc/ssl/skykin/"))
print("==== compose on server ====")
print(run("ls /opt/call-center-deployement/call-center/docker-compose.yml /root/skykin*/docker-compose.yml 2>/dev/null; grep -n '8088\\|18088\\|skykin-web' /opt/call-center-deployement/call-center/docker-compose.yml 2>/dev/null | head"))
c.close()
