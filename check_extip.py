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


def run(cmd, timeout=120):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


print("==== global vars FreeSWITCH is actually using ====")
for v in ("external_rtp_ip", "external_sip_ip", "local_ip_v4", "domain"):
    print(f"  {v} = " + run(f'docker exec skykin-freeswitch fs_cli -x "global_getvar {v}" 2>&1').strip())

print()
print("==== vars.xml external ip lines ====")
print(run(r"""docker exec skykin-freeswitch grep -aE "external_rtp_ip|external_sip_ip" /etc/freeswitch/vars.xml | sed 's/^/  /' """))

print("==== what each profile advertises for RTP (live) ====")
print(run(r"""docker exec skykin-freeswitch fs_cli -x "sofia status profile internal" 2>&1 | grep -aiE "^RTP-IP|^Ext-RTP-IP|^SIP-IP|^Ext-SIP-IP|^URL|^BINDURL" | sed 's/^/  internal  /' """))
print(run(r"""docker exec skykin-freeswitch fs_cli -x "sofia status profile external" 2>&1 | grep -aiE "^RTP-IP|^Ext-RTP-IP|^SIP-IP|^Ext-SIP-IP|^URL|^BINDURL" | sed 's/^/  external  /' """))
c.close()
