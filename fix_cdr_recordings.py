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


def run(cmd, timeout=180):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print("==== web ports ====")
print(run("docker port skykin-web; ss -lnt | grep -E ':80 |:8090|:8088|:8080'"))

print("==== probe import ====")
print(
    run(
        r"""
for u in \
  http://127.0.0.1:8090/app/xml_cdr/xml_cdr_import.php \
  http://127.0.0.1:8080/app/xml_cdr/xml_cdr_import.php \
  http://10.0.0.93:8090/app/xml_cdr/xml_cdr_import.php \
  http://172.18.0.1:80/app/xml_cdr/xml_cdr_import.php; do
  code=$(curl -sS -o /tmp/cdr.out -w '%{http_code}' -u fusionpbx:fusionpbx -X POST "$u" --data 'cdr=' || echo fail)
  echo "$code $u"
done
"""
    )
)
c.close()
