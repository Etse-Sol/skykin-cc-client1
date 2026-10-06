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
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")


print("==== latest 102 ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E 'Processing 102 <|AUDIO RTP \\[sofia/external|has been answered|"
        "Opus decoder stats: Frames\\[' /var/log/freeswitch/freeswitch.log | tail -25\""
    )
)
print("==== pcap last 2 min RTP ====")
print(
    run(
        r"""
python3 - <<'PY'
import subprocess, collections
# summarize UDP 172-byte (PCMA) flows in the pcap
out = subprocess.check_output(
    "tcpdump -nn -r /tmp/ethio.pcap udp and not port 5060 and not port 5080 2>/dev/null | tail -5000",
    shell=True, text=True, errors="replace",
)
flows = collections.Counter()
for line in out.splitlines():
    if " IP " not in line or " > " not in line:
        continue
    try:
        body = line.split(" IP ", 1)[1]
        a, b = body.split(" > ")
        src = a.strip()
        dst = b.split(":")[0].strip()
        flows[(src, dst)] += 1
    except Exception:
        pass
print("top flows in last 5000 media lines:")
for (s,d), n in flows.most_common(12):
    print(f"  {n:5d}  {s} -> {d}")
PY
"""
    )
)
c.close()
