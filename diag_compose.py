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


print("==== server compose (ports + env + volumes) ====")
print(run("sed -n '1,160p' /opt/call-center-deployement/call-center/docker-compose.yml"))

print("==== server .env (non-secret keys) ====")
print(run("grep -E '^[A-Z_]+=' /opt/call-center-deployement/call-center/.env | sed -E 's/(PASSWORD|CRED|SECRET)=.*/\\1=***/'"))

print("==== 101.xml ====")
print(run("docker exec skykin-freeswitch cat /etc/freeswitch/directory/default/101.xml"))

print("==== directory default.xml domain ====")
print(run("docker exec skykin-freeswitch grep -n 'name=\\|domain' /etc/freeswitch/directory/default.xml | head -20"))

print("==== FS container net ====")
print(run("docker inspect skykin-freeswitch --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} ip={{$v.IPAddress}}{{end}}'"))
print(run("docker inspect skykin-db --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} ip={{$v.IPAddress}}{{end}}'"))
print(run("docker port skykin-freeswitch"))

print("==== gateway password length ====")
print(run("""docker exec skykin-db psql -U fusionpbx -d fusionpbx -t -A -c "SELECT length(password), left(password,4) FROM v_gateways WHERE gateway='SIP';" """))

print("==== 10.0.0.93 on container? ====")
print(run("docker exec skykin-freeswitch ip addr show | sed -n '1,40p'"))

c.close()
