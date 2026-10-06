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

run(f"docker exec skykin-freeswitch cat {DP} > /tmp/dp_edit2.xml")
sftp = c.open_sftp()
with sftp.open("/tmp/dp_edit2.xml", "r") as fh:
    xml = fh.read().decode()

# The agent leg needs the public address so the browser can reach us; the carrier
# leg must keep 10.0.0.93, which is how Ethio sees this host. rtp_advertise_ip set
# on the agent leg carries into the outbound leg, so pin it explicitly per bridge.
old = "{absolute_codec_string=^^:PCMA:PCMU,ignore_early_media=true,"
new = "{absolute_codec_string=^^:PCMA:PCMU,rtp_advertise_ip=10.0.0.93,include_external_ip=false,ignore_early_media=true,"
n = xml.count(old)
xml = xml.replace(old, new)
print(f"==== pinning carrier-leg media IP on {n} bridge(s) ====")

with sftp.open("/tmp/dp_new2.xml", "w") as fh:
    fh.write(xml)
sftp.close()

print(run(f"docker exec skykin-freeswitch cp {DP} {DP}.bak_bleg 2>&1"))
print(run(f"docker cp /tmp/dp_new2.xml skykin-freeswitch:{DP} 2>&1 | sed 's/^/  /'"))
print(run('docker exec skykin-freeswitch fs_cli -x "reloadxml" 2>&1 | sed "s/^/  /"'))

print("==== resulting bridge lines ====")
print(run(f"docker exec skykin-freeswitch grep -a 'sofia/gateway' {DP} | sed 's/^/  /'"))

print("==== full SDP of the inbound INVITE (identify payload 112) ====")
print(run(
    "tcpdump -r /tmp/call.pcap -A -s0 -nn 'port 5080' 2>/dev/null "
    "| grep -aE '^(v=|o=|c=|m=|a=)' | head -40 | sed 's/^/  /'"
))
c.close()
