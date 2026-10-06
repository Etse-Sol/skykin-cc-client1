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


print("==== queue extension 8000 (transfer target for inbound DIDs) ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'grep -a -A 12 \"skykin_queue\" /etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml | head -20'"
    " | sed 's/^/  /'"
))

# Inbound DID route. The carrier can present the number with or without +251, so
# match all the forms it might use, then hand the call to the queue in the domain
# context where the agents live.
did_xml = """<include>
  <!-- Inbound calls from the Ethio Telecom trunk. The gateway uses context
       "public", which otherwise only holds FreeSWITCH's 5551212 sample, so
       without this every inbound call was rejected with no route. -->
  <extension name="skykin_inbound_did">
    <condition field="destination_number" expression="^\\+?(?:251)?0?11113875[59]$">
      <action application="set" data="domain_name=client1.skykin.local"/>
      <action application="export" data="domain_name=client1.skykin.local"/>
      <action application="set" data="hangup_after_bridge=true"/>
      <action application="set" data="continue_on_fail=true"/>
      <action application="transfer" data="8000 XML client1.skykin.local"/>
    </condition>
  </extension>
</include>
"""

sftp = c.open_sftp()
with sftp.open("/tmp/01_skykin_did.xml", "w") as fh:
    fh.write(did_xml)
sftp.close()
print("==== installing inbound DID route ====")
print(run(
    "docker cp /tmp/01_skykin_did.xml "
    "skykin-freeswitch:/etc/freeswitch/dialplan/public/01_skykin_did.xml 2>&1 | sed 's/^/  /'"
))

# Force PCMA only had no fallback; if the carrier ever answers with PCMU the leg
# would have no common codec at all.
print("==== widening trunk codec to PCMA,PCMU ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'cp /etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml /tmp/dp.bak && "
    "sed -i \"s/absolute_codec_string=PCMA,/absolute_codec_string=PCMA,PCMU,/g\" "
    "/etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml && "
    "grep -aoE \"absolute_codec_string=[^,}]*(,[A-Z0-9]*)*\" "
    "/etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml | sort -u' 2>&1 | sed 's/^/  /'"
))

print("==== reloading dialplan ====")
print(run('docker exec skykin-freeswitch fs_cli -x "reloadxml" 2>&1 | sed "s/^/  /"'))
print(run('docker exec skykin-freeswitch fs_cli -x "sofia status" 2>&1 | grep -aE "SIP|gateway" | sed "s/^/  /"'))
c.close()
