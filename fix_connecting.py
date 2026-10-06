import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOCAL_PHP = r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


sftp = c.open_sftp()
with open(LOCAL_PHP, "rb") as f:
    data = f.read()
with sftp.file("/opt/call-center-deployement/call-center/app/agent_dashboard/index.php", "wb") as rf:
    rf.write(data)
sftp.close()
print("uploaded php", len(data))

print("==== sipjs bundle ====")
print(run("docker exec skykin-web sh -c 'ls -l /var/www/fusionpbx/app/agent_dashboard/js/sipjs.bundle.js; php -l /var/www/fusionpbx/app/agent_dashboard/index.php'"))

print("==== nginx http2 off + buffering ====")
print(run(r"""
docker exec skykin-web sh -c '
f=/etc/nginx/sites-enabled/skykin.conf
sed -i "s/listen 443 ssl http2;/listen 443 ssl;/" "$f"
# add proxy_buffering off after proxy_http_version if missing
grep -q proxy_buffering "$f" || sed -i "s/proxy_http_version 1.1;/proxy_http_version 1.1;\n        proxy_buffering off;/" "$f"
grep -n "listen 443\\|proxy_buffering\\|location /wss" "$f"
nginx -t && nginx -s reload
'
"""))

print("==== recent nginx errors ====")
print(run("docker exec skykin-web sh -c 'tail -8 /var/log/nginx/error.log'"))
print("==== 102 user exists ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'user_exists id 102 client1.skykin.local'"))
print(run("docker exec skykin-freeswitch ls /etc/freeswitch/directory/default/102.xml"))
c.close()
