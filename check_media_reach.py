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


print("==== reachability of carrier signalling vs media nodes ====")
for ip in ("10.208.233.134", "10.208.233.197", "10.208.233.203"):
    r = run(f"ping -c 2 -W 2 {ip} 2>&1 | tail -2 | head -1")
    print(f"  {ip:18s} {r.strip()}")

print()
print("==== ufw rules for RTP / SIP ====")
print(run("ufw status 2>/dev/null | grep -aE '16384|5060|5080' | sed 's/^/  /'"))

print("==== is 5080/udp reachable from outside into the container? ====")
print(run("iptables -t nat -S DOCKER 2>/dev/null | grep -a 5080 | sed 's/^/  /'") or "  NO DNAT RULE FOR 5080 (inbound trunk calls are dropped)")

print("==== codec string currently forced on the trunk leg ====")
print(run(
    r"""docker exec skykin-freeswitch grep -aoE "absolute_codec_string=[^,}]*" """
    r"""/etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml | sort -u | sed 's/^/  /' """
))

print("==== codecs FreeSWITCH is allowed to use on the external profile ====")
print(run(r"""docker exec skykin-freeswitch grep -aE "codec-prefs|inbound-codec|outbound-codec" /etc/freeswitch/sip_profiles/external.xml | sed 's/^/  /' """))
print(run(r"""docker exec skykin-freeswitch fs_cli -x "global_getvar global_codec_prefs" 2>&1 | sed 's/^/  global_codec_prefs: /' """))
print(run(r"""docker exec skykin-freeswitch fs_cli -x "global_getvar outbound_codec_prefs" 2>&1 | sed 's/^/  outbound_codec_prefs: /' """))
c.close()
