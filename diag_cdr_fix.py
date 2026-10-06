import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    username="root",
    password="Pass@1234",
    timeout=25,
    allow_agent=False,
    look_for_keys=False,
)


def run(cmd, timeout=90):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print("==== fs mounts ====")
print(run("docker inspect skykin-freeswitch --format '{{json .Mounts}}'"))
print("==== xml_cdr.conf ====")
print(run("docker exec skykin-freeswitch cat /etc/freeswitch/autoload_configs/xml_cdr.conf.xml"))
print("==== spool ====")
print(run("docker exec skykin-freeswitch sh -c 'ls -lt /var/log/freeswitch/xml_cdr 2>/dev/null | head -20; ls -lt /usr/local/freeswitch/log/xml_cdr 2>/dev/null | head; find /var/log/freeswitch /usr/local/freeswitch/log -name \"*.cdr.xml\" 2>/dev/null | head'"))
print("==== curl import ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "'curl -sI http://web/app/xml_cdr/xml_cdr_import.php; echo ----; "
        "curl -skI https://web/app/xml_cdr/xml_cdr_import.php; echo ----; "
        "curl -sI http://skykin-web/app/xml_cdr/xml_cdr_import.php; echo ----; "
        "getent hosts web; getent hosts skykin-web'"
    )
)
print("==== web recordings tree ====")
print(run("docker exec skykin-web sh -c 'ls -la /var/lib/freeswitch/recordings; ls -la /var/lib/freeswitch/recordings/client1.skykin.local 2>/dev/null'"))
print("==== host recordings ====")
print(run("ls -la /var/lib/docker/volumes/call-center_skykin_recordings/_data/client1.skykin.local 2>/dev/null | head"))
print(run("docker inspect skykin-freeswitch --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'"))
c.close()
