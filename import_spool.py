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


def run(cmd, timeout=300):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print("==== web spool ====")
print(run("docker exec skykin-web sh -c 'ls -la /var/log/freeswitch/xml_cdr | head -8; echo count=$(ls /var/log/freeswitch/xml_cdr/*.cdr.xml 2>/dev/null | wc -l)'"))
print("==== php import once ====")
print(run("docker exec skykin-web php /var/www/fusionpbx/app/xml_cdr/xml_cdr_import.php 2>&1 | tail -30"))
print("==== after one cli ====")
print(run("docker exec skykin-web sh -c 'echo left=$(ls /var/log/freeswitch/xml_cdr/*.cdr.xml 2>/dev/null | wc -l)'"))
c.close()
