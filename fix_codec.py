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

print("==== restoring the pre-edit dialplan ====")
print(run(f"docker exec skykin-freeswitch sh -c 'cp /tmp/dp.bak {DP} && echo restored' 2>&1 | sed 's/^/  /'"))

# Inside {} a comma separates channel variables, so a codec list has to use the
# ^^ delimiter form or PCMU would be parsed as a variable name.
print("==== applying correct multi-codec syntax ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    f"'sed -i \"s/absolute_codec_string=PCMA,/absolute_codec_string=^^:PCMA:PCMU,/g\" {DP} && echo ok' 2>&1 | sed 's/^/  /'"
))

print("==== resulting bridge lines (verify they are well formed) ====")
print(run(f"docker exec skykin-freeswitch grep -a 'application=\"bridge\"' {DP} | sed 's/^/  /'"))

print("==== reload ====")
print(run('docker exec skykin-freeswitch fs_cli -x "reloadxml" 2>&1 | sed "s/^/  /"'))
c.close()
