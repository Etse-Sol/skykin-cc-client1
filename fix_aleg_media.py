import re
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


def run(cmd, timeout=250):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


DP = "/etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml"

print("==== internal profile NAT/media handling for browsers ====")
print(run(
    r"""docker exec skykin-freeswitch grep -aE "local-network-acl|apply-nat-acl|ext-rtp-ip|aggressive-nat" """
    r"""/etc/freeswitch/sip_profiles/internal.xml | sed 's/^/  /' """
))

print("==== which extensions advertise the public IP to the browser? ====")
print(run(
    f"docker exec skykin-freeswitch grep -aE 'extension name=|rtp_advertise_ip|include_external_ip' {DP} "
    "| sed 's/^/  /'"
))

# Pull the dialplan out so the edit is exact.
run(f"docker exec skykin-freeswitch cat {DP} > /tmp/dp_edit.xml")
sftp = c.open_sftp()
with sftp.open("/tmp/dp_edit.xml", "r") as fh:
    xml = fh.read().decode()

before = xml
# The queue and echo extensions export rtp_advertise_ip so FreeSWITCH offers the
# browser its public address; the outbound rules were missing it, so the agent leg
# had nowhere to send audio. Use "set" rather than "export" so the carrier leg keeps
# advertising 10.0.0.93, which is the address Ethio expects.
inject = (
    '      <action application="set" data="rtp_advertise_ip=196.189.236.140"/>\n'
    '      <action application="set" data="include_external_ip=true"/>\n'
)
count = 0
out_parts = []
for block in re.split(r'(?=<extension name=")', xml):
    m = re.match(r'<extension name="(skykin_outbound_et_[a-z0-9]+)"', block)
    if m and "rtp_advertise_ip" not in block and '<action application="answer"/>' in block:
        block = block.replace('      <action application="answer"/>\n', inject + '      <action application="answer"/>\n', 1)
        count += 1
    out_parts.append(block)
xml = "".join(out_parts)

print(f"==== patched {count} outbound extension(s) ====")
if count and xml != before:
    with sftp.open("/tmp/dp_new.xml", "w") as fh:
        fh.write(xml)
    sftp.close()
    print(run(f"docker exec skykin-freeswitch cp {DP} {DP}.bak_media 2>&1"))
    print(run(f"docker cp /tmp/dp_new.xml skykin-freeswitch:{DP} 2>&1 | sed 's/^/  /'"))
    print(run('docker exec skykin-freeswitch fs_cli -x "reloadxml" 2>&1 | sed "s/^/  /"'))
else:
    sftp.close()
    print("  nothing to change")

print("==== verify one patched rule ====")
print(run(
    f"docker exec skykin-freeswitch sh -c 'grep -a -A 14 \"skykin_outbound_et_zero\" {DP}' | sed 's/^/  /'"
))
c.close()
