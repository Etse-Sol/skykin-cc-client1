import struct
import sys
from collections import defaultdict

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
sftp = c.open_sftp()
data = sftp.open("/tmp/carrier.pcap", "rb").read()
sftp.close()
c.close()

magic = struct.unpack("<I", data[:4])[0]
endian = "<" if magic in (0xA1B2C3D4, 0xA1B23C4D) else ">"
nano = magic in (0xA1B23C4D, 0x4D3CB2A1)
off = 24
streams = defaultdict(list)
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
    if sport == 5060 or dport == 5060 or len(pl) < 12:
        continue
    if (pl[0] >> 6) != 2:
        continue
    pt = pl[1] & 0x7F
    if pt >= 72:  # RTCP range
        continue
    marker = (pl[1] >> 7) & 1
    seq, tstamp, ssrc = struct.unpack("!HII", pl[2:12])
    ts = ts_s + (ts_u / 1e9 if nano else ts_u / 1e6)
    streams[(src, sport, dport)].append((ts, pt, marker, seq, tstamp, ssrc, len(pl) - 12))

print("==== RTP header health per stream ====")
for key in sorted(streams, key=lambda k: -len(streams[k])):
    src, sport, dport = key
    pk = streams[key]
    who = "US -> CARRIER" if src == "10.0.0.93" else "CARRIER -> US"
    ssrcs = {p[5] for p in pk}
    pts = {p[1] for p in pk}
    sizes = {p[6] for p in pk}
    markers = sum(p[2] for p in pk)
    seqs = [p[3] for p in pk]
    gaps = 0
    resets = 0
    for i in range(1, len(seqs)):
        d = (seqs[i] - seqs[i - 1]) & 0xFFFF
        if d == 0:
            continue
        if d > 1:
            gaps += 1
        if d > 1000 and d < 64000:
            resets += 1
    dur = pk[-1][0] - pk[0][0]
    print(f"\n  {who} :{sport} -> :{dport}   {len(pk)} packets over {dur:.1f}s")
    print(f"    SSRC(s)          : {[hex(s) for s in ssrcs]}  {'<-- CHANGES MID-CALL' if len(ssrcs) > 1 else 'stable'}")
    print(f"    payload type(s)  : {sorted(pts)}")
    print(f"    payload bytes    : {sorted(sizes)}")
    print(f"    marker bits set  : {markers}")
    print(f"    seq gaps         : {gaps}   large seq jumps: {resets}")
    print(f"    packets/sec      : {len(pk) / dur if dur else 0:.1f}")
