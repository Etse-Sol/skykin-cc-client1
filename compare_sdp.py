import re
import struct
import sys

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
msgs = []
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
    if 5060 not in (sport, dport):
        continue
    body = udp[8:].decode("utf-8", "replace")
    ts = ts_s + (ts_u / 1e9 if nano else ts_u / 1e6)
    msgs.append((ts, src, body))

print("==== every SIP message that carried SDP, with its media address ====")
t0 = msgs[0][0] if msgs else 0
for ts, src, body in msgs:
    first = body.split("\r\n", 1)[0][:60]
    conn = re.findall(r"c=IN IP4 ([0-9.]+)", body)
    media = re.findall(r"m=audio (\d+)", body)
    if not conn and not media:
        continue
    who = "us  " if src == "10.0.0.93" else "them"
    print(f"  +{ts - t0:7.2f}s {who} | {first}")
    for i, m in enumerate(media):
        ip_ = conn[i] if i < len(conn) else (conn[0] if conn else "?")
        print(f"            media -> {ip_}:{m}")

print("\n==== conclusion check ====")
print("  Compare the media address in the 183 Session Progress against the 200 OK.")
print("  If the 200 OK differs and we kept sending to the 183's port, that is why")
print("  the far end cannot hear the agent.")
