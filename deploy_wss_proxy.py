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
print("uploaded", len(data))
print(run("docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/index.php"))
print(run("docker exec skykin-web grep -n \"agent_wss\\|8088/wss\\|5060\" /var/www/fusionpbx/app/agent_dashboard/index.php | head -10"))
print("==== nginx wss ====")
print(run("docker exec skykin-web sh -c 'grep -n -A6 \"location /wss\" /etc/nginx/sites-enabled/* /etc/nginx/conf.d/* /etc/nginx/nginx.conf 2>/dev/null | head -40'"))
print("==== regs / bind ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal' | grep -E 'WSS-BIND|BIND-URL|REGISTRATIONS'"))
print(run("docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg' | grep -E 'User:|Status:|IP:'"))
c.close()
