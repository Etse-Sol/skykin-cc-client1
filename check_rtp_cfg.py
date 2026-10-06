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


def run(cmd, timeout=200):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


print("==== FreeSWITCH RTP port range (switch.conf.xml) ====")
print(run(r"""docker exec skykin-freeswitch grep -aE "rtp-start-port|rtp-end-port" /etc/freeswitch/autoload_configs/switch.conf.xml | sed 's/^/  /' """))

print("==== Docker published RTP range (min/max) ====")
print(run(r"""docker port skykin-freeswitch | grep -oE '^[0-9]+/udp' | grep -oE '^[0-9]+' | sort -n | sed -n '1p;$p' | sed 's/^/  /' """))
print("  total udp ports published: " + run(r"""docker port skykin-freeswitch | grep -c 'udp' """).strip())

print("==== external profile media params ====")
print(run(r"""docker exec skykin-freeswitch grep -aE "rtp-ip|ext-rtp-ip|apply-nat-acl|rtp-autoflush|disable-rtp-auto-adjust|rtp-timeout|media_timeout|local-network-acl|aggressive-nat" /etc/freeswitch/sip_profiles/external.xml | sed 's/^/  /' """))

print("==== container interfaces (does 10.0.0.93 exist inside?) ====")
print(run(r"""docker exec skykin-freeswitch ip -4 addr show | grep -aE "inet " | sed 's/^/  /' """))

print("==== live RTP port range in use by FreeSWITCH ====")
print(run(r"""docker exec skykin-freeswitch fs_cli -x "global_getvar rtp_start_port" 2>&1 | sed 's/^/  start: /' """))
print(run(r"""docker exec skykin-freeswitch fs_cli -x "global_getvar rtp_end_port" 2>&1 | sed 's/^/  end:   /' """))
c.close()
