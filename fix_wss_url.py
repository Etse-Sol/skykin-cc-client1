import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


# Pull, patch with Python on the host, push back (volume-mounted file).
print(run("docker exec skykin-web cat /var/www/fusionpbx/app/agent_dashboard/index.php > /tmp/ad_index.php; wc -c /tmp/ad_index.php"))

sftp = c.open_sftp()
data = sftp.open("/tmp/ad_index.php", "r").read()
if isinstance(data, bytes):
    text = data.decode("utf-8", "replace")
else:
    text = data

# Fix the botched sed first, then apply the intended URLs.
text = text.replace(". '':7443'", ". ':7443'")
text = text.replace("pagePort + '':7443'", "':7443'")
text = text.replace(") + '':7443'", ") + ':7443'")
text = text.replace("'' + '':7443'", "':7443'")

old_php = "$agent_wss      = 'wss://' . preg_replace('/:\\d+$/', '', $_SERVER['HTTP_HOST']) . ':7443';"
# after botched fix it may already be :7443
if "/wss/" in text and "$agent_wss" in text:
    text = text.replace(
        "$agent_wss      = 'wss://' . preg_replace('/:\\d+$/', '', $_SERVER['HTTP_HOST']) . '/wss/';",
        old_php,
    )

# buildSipWsUrl: force 7443 on https
old_fn = """function buildSipWsUrl(host, port) {
    const cleanHost = String(host || location.hostname)
        .replace(/^wss?:\\/\\//i, '').replace(/\\/.*$/, '').replace(/:\\d+$/, '');
    const scheme = location.protocol === 'https:' ? 'wss://' : 'ws://';"""

# Replace the return paths inside buildSipWsUrl more bluntly
text = text.replace("return scheme + location.hostname + pagePort + '/wss/';",
                    "return scheme + location.hostname + ':7443';")
text = text.replace("return scheme + cleanHost + pagePort + '/wss/';",
                    "return scheme + cleanHost + ':7443';")
text = text.replace("return scheme + location.hostname + ':7443';",
                    "return scheme + location.hostname + ':7443';")

# sipBridge.init fallbacks
text = text.replace(" + '/wss/';", " + ':7443';")
text = text.replace(" + '':7443';", " + ':7443';")

sftp.open("/tmp/ad_index.php", "w").write(text)
sftp.close()

print(run("docker cp /tmp/ad_index.php skykin-web:/var/www/fusionpbx/app/agent_dashboard/index.php"))
print(run("docker exec skykin-web php -l /var/www/fusionpbx/app/agent_dashboard/index.php"))
print(run("docker exec skykin-web grep -n \"agent_wss\\|7443\\|/wss/\" /var/www/fusionpbx/app/agent_dashboard/index.php | head -25"))
c.close()
