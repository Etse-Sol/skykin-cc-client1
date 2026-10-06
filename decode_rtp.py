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


print("==== capture ====")
print(run("ls -l /tmp/carrier.pcap 2>&1 | sed 's/^/  /'"))

print("==== why did the call end? ====")
L = "/var/log/freeswitch/freeswitch.log"
print(run(
    f"docker exec skykin-freeswitch sh -c 'tail -40000 {L} 2>/dev/null' | "
    "grep -aiE 'Hangup sofia/external|Hangup sofia/internal|hangup_cause|BYE|session.timer|media timeout|rtp timeout|Session-Expires|MEDIA_TIMEOUT' "
    "| tail -25 | sed 's/^/  /'"
))

sftp = c.open_sftp()
data = sftp.open("/tmp/carrier.pcap", "rb").read()
sftp.close()
c.close()

# Minimal pcap reader (Ethernet link type) so RTP payloads can be decoded.
if len(data) < 24:
    print("empty capture")
    sys.exit(0)
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
    dst = ".".join(str(b) for b in ip[16:20])
    udp = ip[ihl:]
    sport, dport = struct.unpack("!HH", udp[:4])
    payload = udp[8:]
    if sport == 5060 or dport == 5060 or len(payload) < 13:
        continue
    pt = payload[1] & 0x7F
    ts = ts_s + (ts_u / 1e9 if nano else ts_u / 1e6)
    flows[(src, sport, dst, dport, pt)].append((ts, payload[12:]))

print("\n==== decoded audio levels of each RTP stream ====")
if not flows:
    print("  no RTP captured")
for key in sorted(flows, key=lambda k: -len(flows[k])):
    src, sport, dst, dport, pt = key
    pkts = flows[key]
    name = "PCMA" if pt == 8 else ("PCMU" if pt == 0 else f"pt{pt}")
    who = "US -> CARRIER" if src.startswith("10.0.0.93") else "CARRIER -> US"
    print(f"\n  {who}  {src}:{sport} -> {dst}:{dport}  {name}  {len(pkts)} packets")
    if pt != 8:
        print("    (not A-law, skipping level decode)")
        continue
    t0 = pkts[0][0]
    buckets = defaultdict(list)
    for ts, pl in pkts:
        buckets[int(ts - t0)].extend(ALAW[b] for b in pl)
    print("    sec | rms      | verdict")
    for s in sorted(buckets)[:30]:
        v = buckets[s]
        r = math.sqrt(sum(x * x for x in v) / len(v)) if v else 0.0
        verdict = "SILENCE" if r < 60 else ("faint" if r < 300 else "AUDIO")
        print(f"    {s:3d} | {r:8.1f} | {verdict}")
