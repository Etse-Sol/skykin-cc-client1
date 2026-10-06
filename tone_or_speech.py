import math
import struct
import sys
from collections import defaultdict

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def alaw_table():
    tbl = []
    for a in range(256):
        v = a ^ 0x55
        t = (v & 0x0F) << 4
        seg = (v & 0x70) >> 4
        if seg == 0:
            t += 8
        elif seg == 1:
            t += 0x108
        else:
            t += 0x108
            t <<= seg - 1
        tbl.append(t if (v & 0x80) else -t)
    return tbl


ALAW = alaw_table()

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=250):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


print("==== does the carrier send RTCP, and do we answer it? ====")
print(run(
    "tcpdump -r /tmp/carrier.pcap -qnn 'udp' 2>/dev/null "
    "| grep -aoE '[0-9.]+\\.[0-9]+ > [0-9.]+\\.[0-9]+' | sort | uniq -c | sort -rn | head -12 | sed 's/^/  /'"
))
print("  ICMP port-unreachable we send back (rejected RTCP):")
print(run("tcpdump -r /tmp/carrier.pcap -qnn 'icmp' 2>/dev/null | wc -l | sed 's/^/    count: /'"))
print(run("tcpdump -r /tmp/carrier.pcap -qnn 'icmp' 2>/dev/null | head -3 | sed 's/^/    /'"))

sftp = c.open_sftp()
data = sftp.open("/tmp/carrier.pcap", "rb").read()
sftp.close()
c.close()

magic = struct.unpack("<I", data[:4])[0]
endian = "<" if magic in (0xA1B2C3D4, 0xA1B23C4D) else ">"
nano = magic in (0xA1B23C4D, 0x4D3CB2A1)
off = 24
flows = defaultdict(list)
while off + 16 <= len(data):
    ts_s, ts_u, caplen, _ = struct.unpack(endian + "IIII", data[off:off + 16])
    off += 16
    pkt = data[off:off + caplen]
    off += caplen
    if len(pkt) < 34 or struct.unpack("!H", pkt[12:14])[0] != 0x0800:
        continue
    ihl = (pkt[14] & 0x0F) * 4
    ip = pkt[14:]
    if len(ip) < ihl + 8 or ip[9] != 17:
        continue
    src = ".".join(str(b) for b in ip[12:16])
    udp = ip[ihl:]
    sport, dport = struct.unpack("!HH", udp[:4])
    pl = udp[8:]
    if sport == 5060 or dport == 5060 or len(pl) < 13 or (pl[1] & 0x7F) != 8:
        continue
    ts = ts_s + (ts_u / 1e9 if nano else ts_u / 1e6)
    flows[src].append((ts, pl[12:]))

# A 440/480 Hz ringback tone crosses zero ~900-960 times per second and has a
# near-constant level. Speech is broadband and its level fluctuates, so zero
# crossings separate "we forwarded the agent" from "we forwarded a tone".
print("\n==== is our transmitted stream speech or a ringback tone? ====")
for src, pkts in flows.items():
    who = "US -> CARRIER" if src == "10.0.0.93" else "CARRIER -> US"
    t0 = pkts[0][0]
    buckets = defaultdict(list)
    for ts, pl in pkts:
        buckets[int(ts - t0)].extend(ALAW[b] for b in pl)
    print(f"\n  {who} ({src})")
    print("    sec |     rms | zero-crossings/s | looks like")
    for s in sorted(buckets)[:22]:
        v = buckets[s]
        if len(v) < 100:
            continue
        r = math.sqrt(sum(x * x for x in v) / len(v))
        zc = sum(1 for i in range(1, len(v)) if (v[i - 1] >= 0) != (v[i] >= 0))
        zc_per_s = zc * 8000 / len(v)
        if r < 60:
            kind = "silence"
        elif 820 <= zc_per_s <= 1050 and r > 500:
            kind = "TONE (ringback)"
        else:
            kind = "speech/voice"
        print(f"    {s:3d} | {r:7.1f} | {zc_per_s:16.0f} | {kind}")
