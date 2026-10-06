import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=250):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


DP = "/etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml"
DID = "/etc/freeswitch/dialplan/public/01_skykin_did.xml"

run(f"docker exec skykin-freeswitch cat {DP} > /tmp/dp3.xml")
sftp = c.open_sftp()
with sftp.open("/tmp/dp3.xml", "r") as fh:
    xml = fh.read().decode()

# Ethio's IMS core sends RTCP to our RTP port + 1 and we never answered it, so the
# carrier had no receiver reports for the stream carrying the agent's voice.
old = "{absolute_codec_string=^^:PCMA:PCMU,rtp_advertise_ip=10.0.0.93,"
new = "{absolute_codec_string=^^:PCMA:PCMU,rtcp_audio_interval_msec=5000,rtp_advertise_ip=10.0.0.93,"
n = xml.count(old)
xml = xml.replace(old, new)
print(f"==== enabling RTCP on {n} outbound bridge(s) ====")
if n:
    with sftp.open("/tmp/dp3_new.xml", "w") as fh:
        fh.write(xml)
    print(run(f"docker exec skykin-freeswitch cp {DP} {DP}.bak_rtcp 2>&1"))
    print(run(f"docker cp /tmp/dp3_new.xml skykin-freeswitch:{DP} 2>&1 | sed 's/^/  /'"))

# Same for inbound calls arriving from the trunk.
run(f"docker exec skykin-freeswitch cat {DID} > /tmp/did3.xml")
with sftp.open("/tmp/did3.xml", "r") as fh:
    did = fh.read().decode()
if "rtcp_audio_interval_msec" not in did:
    did = did.replace(
        '<action application="set" data="domain_name=client1.skykin.local"/>',
        '<action application="set" data="rtcp_audio_interval_msec=5000"/>\n'
        '      <action application="set" data="domain_name=client1.skykin.local"/>',
        1,
    )
    with sftp.open("/tmp/did3_new.xml", "w") as fh:
        fh.write(did)
    print("==== enabling RTCP on inbound trunk calls ====")
    print(run(f"docker cp /tmp/did3_new.xml skykin-freeswitch:{DID} 2>&1 | sed 's/^/  /'"))
sftp.close()

print(run('docker exec skykin-freeswitch fs_cli -x "reloadxml" 2>&1 | sed "s/^/  /"'))
print("==== verify ====")
print(run(f"docker exec skykin-freeswitch grep -ao 'rtcp_audio_interval_msec=[0-9]*' {DP} {DID} | sed 's/^/  /'"))
c.close()
