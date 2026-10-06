import struct
import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=250):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


print("==== capture on disk ====")
print(run("ls -l /tmp/carrier.pcap 2>&1 | sed 's/^/  /'"))

sftp = c.open_sftp()
data = sftp.open("/tmp/carrier.pcap", "rb").read()
sftp.close()

magic = struct.unpack("<I", data[:4])[0]
endian = "<" if magic in (0xA1B2C3D4, 0xA1B23C4D) else ">"
off = 24
our_ssrcs = set()
rtcp = []
while off + 16 <= len(data):
    _, _, caplen, _ = struct.unpack(endian + "IIII", data[off:off + 16])
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
    if sport == 5060 or dport == 5060 or len(pl) < 8:
        continue
    pt = pl[1] & 0x7F
    if pt < 72:
        if src == "10.0.0.93":
            our_ssrcs.add(struct.unpack("!I", pl[8:12])[0])
        continue
    rtcp.append((src, sport, dport, pl))

print(f"\n  our RTP SSRCs: {[hex(s) for s in our_ssrcs]}")
print(f"  RTCP packets captured: {len(rtcp)}")

print("\n==== decoding RTCP report blocks ====")
found_reports = 0
for src, sport, dport, pl in rtcp:
    who = "US -> CARRIER" if src == "10.0.0.93" else "CARRIER -> US"
    i = 0
    while i + 4 <= len(pl):
        rc = pl[i] & 0x1F
        ptype = pl[i + 1]
        length = struct.unpack("!H", pl[i + 2:i + 4])[0]
        blk = pl[i:i + (length + 1) * 4]
        if ptype in (200, 201) and len(blk) >= 8:
            sender_ssrc = struct.unpack("!I", blk[4:8])[0]
            base = 8 + (20 if ptype == 200 else 0)
            name = "SR" if ptype == 200 else "RR"
            print(f"\n  {who} {name} from SSRC {hex(sender_ssrc)}  ({sport}->{dport})")
            for r in range(rc):
                o = base + r * 24
                if o + 24 > len(blk):
                    break
                ssrc, frac, cum, ehsn, jit, lsr, dlsr = struct.unpack(
                    "!IBxxxIIIII"[:1] + "I", blk[o:o + 4]
                )[0], blk[o + 4], int.from_bytes(blk[o + 5:o + 8], "big"), \
                    struct.unpack("!I", blk[o + 8:o + 12])[0], \
                    struct.unpack("!I", blk[o + 12:o + 16])[0], \
                    struct.unpack("!I", blk[o + 16:o + 20])[0], \
                    struct.unpack("!I", blk[o + 20:o + 24])[0]
                mine = " <-- THIS IS OUR AUDIO STREAM" if ssrc in our_ssrcs else ""
                print(f"    reporting on SSRC {hex(ssrc)}{mine}")
                print(f"      fraction lost      : {frac} / 256  ({frac * 100 // 256}%)")
                print(f"      cumulative lost    : {cum}")
                print(f"      highest seq recvd  : {ehsn & 0xFFFF} (cycles {ehsn >> 16})")
                print(f"      jitter             : {jit}")
                found_reports += 1
        i += (length + 1) * 4
        if length == 0:
            break

if not found_reports:
    print("  No report blocks found (carrier sent only sender reports or none).")

# Fresh capture so the next call is recorded with our RTCP now enabled.
run("pkill tcpdump >/dev/null 2>&1; rm -f /tmp/rtcp2.pcap")
run("nohup timeout 420 tcpdump -s 0 -nni enp4s3 'udp and net 10.208.233.0/24' -w /tmp/rtcp2.pcap 2>/dev/null & echo ok")
print("\n==== new capture armed for 7 minutes (RTCP now enabled) ====")
c.close()
