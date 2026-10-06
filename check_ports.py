import re
import struct
import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=90):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace") + err.read().decode(errors="replace")


sftp = c.open_sftp()
data = sftp.open("/tmp/carrier.pcap", "rb").read()
sftp.close()

endian = "<" if struct.unpack("<I", data[:4])[0] in (0xA1B2C3D4, 0xA1B23C4D) else ">"
off = 24
sdp_ports = []          # what we told the carrier to send to / where we send from
rtp_flows = {}          # (srcip,sport,dstip,dport) -> count
while off + 16 <= len(data):
    _, _, caplen, _ = struct.unpack(endian + "IIII", data[off:off + 16])
    off += 16
    pkt = data[off:off + caplen]
    off += caplen
    if len(pkt) < 34 or struct.unpack("!H", pkt[12:14])[0] != 0x0800:
        continue
    ip = pkt[14:]
    ihl = (ip[0] & 0x0F) * 4
    if len(ip) < ihl + 8 or ip[9] != 17:
        continue
    src = ".".join(str(b) for b in ip[12:16])
    dst = ".".join(str(b) for b in ip[16:20])
    udp = ip[ihl:]
    sport, dport = struct.unpack("!HH", udp[:4])
    pl = udp[8:]
    if sport == 5060 or dport == 5060:
        txt = pl.decode("utf-8", "replace")
        if "m=audio" in txt and src == "10.0.0.93":
            first = txt.split("\r\n", 1)[0][:44]
            conn = re.search(r"c=IN IP4 ([\d.]+)", txt)
            media = re.search(r"m=audio (\d+)", txt)
            sdp_ports.append((first, conn.group(1) if conn else "?",
                              media.group(1) if media else "?"))
        continue
    if len(pl) >= 12 and (pl[1] & 0x7F) < 72:
        k = (src, sport, dst, dport)
        rtp_flows[k] = rtp_flows.get(k, 0) + 1

print("==== SDP we sent to the carrier (our media address we ask them to use) ====")
for first, conn, media in sdp_ports:
    print(f"  {first:<44} -> c={conn}  m=audio {media}")

print("\n==== actual RTP flows seen leaving/entering our NIC ====")
for (src, sport, dst, dport), n in sorted(rtp_flows.items(), key=lambda x: -x[1]):
    who = "US -> CARRIER" if src == "10.0.0.93" else "CARRIER -> US"
    print(f"  {who:<14} {src}:{sport} -> {dst}:{dport}   {n} packets")

print("\n==== does our RTP source port match what we advertised? ====")
adv = {p for _, _, p in sdp_ports if p.isdigit()}
used = {str(sp) for (src, sp, _, _) in rtp_flows if src == "10.0.0.93"}
print(f"  advertised in SDP : {sorted(adv)}")
print(f"  actually sent from: {sorted(used)}")
print(f"  match: {'YES' if used & adv else 'NO -- carrier would drop our RTP'}")

print("\n==== can we even reach the carrier media subnet? ====")
print(run("for ip in 10.208.233.134 10.208.233.197 10.208.233.203; do "
          "printf '  %-16s ' $ip; "
          "ping -c 2 -W 2 $ip >/dev/null 2>&1 && echo 'ping OK' || echo 'no ICMP reply'; done"))
print(run("  ip route get 10.208.233.203 2>&1 | sed 's/^/  route: /'"))

print("==== host NAT for container RTP ====")
print(run("iptables -t nat -S POSTROUTING 2>&1 | grep -i masq | sed 's/^/  /'"))
c.close()
