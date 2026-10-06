"""Decode the PCMA payloads we send to / receive from the carrier.

Ethio's trunk uses plain RTP, so measuring the audio level inside the packets
shows whether the agent's voice is really being forwarded or whether we are
transmitting silence.
"""
import math
import struct
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# G.711 A-law -> 16-bit linear lookup table.
def _alaw(a):
    a ^= 0x55
    t = (a & 0x0F) << 4
    seg = (a & 0x70) >> 4
    if seg == 0:
        t += 8
    elif seg == 1:
        t += 0x108
    else:
        t = (t + 0x108) << (seg - 1)
    return t if (a & 0x80) else -t


ALAW = [_alaw(i) for i in range(256)]

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


print(run("ls -l /tmp/carrier.pcap 2>&1 | sed 's/^/  /'"))
print(run("pgrep -c tcpdump 2>&1 | sed 's/^/  tcpdump running: /'"))
print(run(
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -A -F' | ' -c "
    "\"SELECT start_stamp, caller_id_number, destination_number, billsec FROM v_xml_cdr "
    "WHERE start_stamp > now() - interval '12 minutes' ORDER BY start_stamp DESC LIMIT 5;\" 2>&1 | sed 's/^/  /'"
))

sftp = c.open_sftp()
try:
    data = sftp.open("/tmp/carrier.pcap", "rb").read()
finally:
    sftp.close()
    c.close()

if len(data) < 24:
    print("  capture is empty - no call was placed in the window")
    sys.exit(0)

magic = data[:4]
endian = "<" if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1") else ">"
nano = magic in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")
linktype = struct.unpack(endian + "I", data[20:24])[0]
print(f"\n  pcap bytes={len(data)} linktype={linktype}")

off = 24
flows = {}
while off + 16 <= len(data):
    ts_s, ts_u, incl, _orig = struct.unpack(endian + "IIII", data[off:off + 16])
    off += 16
    pkt = data[off:off + incl]
    off += incl
    if len(pkt) < 34:
        continue

    l2 = 14 if linktype == 1 else (16 if linktype == 113 else 14)
    if linktype == 1 and pkt[12:14] != b"\x08\x00":
        continue
    ip = pkt[l2:]
    if len(ip) < 20 or (ip[0] >> 4) != 4 or ip[9] != 17:
        continue
    ihl = (ip[0] & 0x0F) * 4
    src = ".".join(str(b) for b in ip[12:16])
    dst = ".".join(str(b) for b in ip[16:20])
    udp = ip[ihl:]
    if len(udp) < 8:
        continue
    sport, dport = struct.unpack("!HH", udp[0:4])
    if sport == 5060 or dport == 5060:
        continue
    rtp = udp[8:]
    if len(rtp) < 13 or (rtp[0] >> 6) != 2:
        continue
    pt = rtp[1] & 0x7F
    if pt != 8:  # PCMA only
        continue
    cc = rtp[0] & 0x0F
    payload = rtp[12 + 4 * cc:]
    if not payload:
        continue

    ts = ts_s + (ts_u / 1e9 if nano else ts_u / 1e6)
    key = f"{src}:{sport} -> {dst}:{dport}"
    f = flows.setdefault(key, {"t0": ts, "sec": {}})
    bucket = int(ts - f["t0"])
    acc = f["sec"].setdefault(bucket, [0, 0])
    for b in payload:
        v = ALAW[b]
        acc[0] += v * v
        acc[1] += 1

if not flows:
    print("  no PCMA RTP found in the capture")
    sys.exit(0)

for key, f in sorted(flows.items(), key=lambda kv: -sum(v[1] for v in kv[1]["sec"].values())):
    total_n = sum(v[1] for v in f["sec"].values())
    total_e = sum(v[0] for v in f["sec"].values())
    overall = math.sqrt(total_e / total_n) if total_n else 0
    label = "WE SEND -> carrier" if key.startswith("10.0.0.93") else "carrier -> US"
    print(f"\n  {label}   {key}")
    print(f"    samples={total_n}  overall RMS={overall:.1f}")
    print("    per-second RMS: ", end="")
    for s in sorted(f["sec"]):
        e, n = f["sec"][s]
        print(f"{math.sqrt(e / n):.0f} ", end="")
    print()
