import re

path = r"C:\Users\hp\.cursor\projects\c-Users-hp-skykin-fusionpbx\agent-transcripts\f8a5cb0a-58fe-4579-985a-fd51cc0980ca\f8a5cb0a-58fe-4579-985a-fd51cc0980ca.jsonl"
last_ts = None
out = []
keys = [
    "Answer failed",
    "Answered Failed",
    "DTLS fingerprint",
    "media_webrtc",
    "sip-udp",
    "ALWAYS WebRTC",
    "UDP-vs-WebRTC",
    "iwjikl",
    "koc74i",
    "s3exgm",
    "still sip-udp",
    "silent",
    "TEMPORARY_FAILURE",
]
with open(path, "r", encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f, 1):
        m = re.search(r"<timestamp>([^<]+)</timestamp>", line)
        if m:
            last_ts = m.group(1)
        if not last_ts or "Sep 18" not in last_ts:
            continue
        for k in keys:
            if k.lower() in line.lower():
                u = re.search(r"<user_query>\s*(.{0,180})", line)
                a = re.search(r'"text":"(.{0,180})', line)
                sn = (u.group(1) if u else (a.group(1) if a else ""))[:160]
                sn = sn.replace("\n", " ")
                out.append("%s | L%s | %s | %s" % (last_ts, i, k, sn))
                break

out_path = r"C:\Users\hp\skykin-fusionpbx\_ts_ans.txt"
with open(out_path, "w", encoding="utf-8") as w:
    w.write("\n".join(out))
print("wrote", len(out))
for row in out:
    print(row)
