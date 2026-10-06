import array
import io
import math
import sys
import wave
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UUID = "0b6c4af5-04ca-44fb-a857-5b3cb068aea5"
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
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== opus / rtp / reneg for this uuid ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        f"\"grep -n '{UUID}\\|84db0188-fe85-4ba1-a3d6-3b3e20587dbf' "
        "/var/log/freeswitch/freeswitch.log | "
        "grep -iE 'Opus|RTP STATS|bytes|jitter|PLC|reneg|SRTP|DTLS|resampler|read_codec|write_codec|Audio Codec' "
        '| tail -80"'
    )
)

print("==== find recording ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        f"'find /var/lib/freeswitch/recordings -name \"{UUID}*\" -ls'"
    )
)

src = (
    "/var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/"
    f"{UUID}.wav"
)
print(run(f"docker cp skykin-freeswitch:{src} /tmp/an.wav; ls -l /tmp/an.wav"))

sftp = c.open_sftp()
try:
    data = sftp.open("/tmp/an.wav", "rb").read()
except Exception as e:
    print("fetch failed", e)
    data = b""
sftp.close()
c.close()

if not data:
    sys.exit(0)


def rms(samples):
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


w = wave.open(io.BytesIO(data), "rb")
ch, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
raw = w.readframes(frames)
w.close()
print(f"\nchannels={ch} rate={rate} width={width} duration={frames / float(rate):.1f}s")
pcm = array.array("h")
pcm.frombytes(raw[: (len(raw) // 2) * 2])
if ch != 2:
    print("mono rms", rms(pcm.tolist()))
else:
    left, right = pcm[0::2], pcm[1::2]
    print(f"ch0 overall rms={rms(left.tolist()):.1f}  ch1 overall rms={rms(right.tolist()):.1f}")
    print("sec |     ch0 |     ch1")
    for s in range(0, int(frames / rate)):
        a = left[s * rate : (s + 1) * rate].tolist()
        b = right[s * rate : (s + 1) * rate].tolist()
        print(f"{s:3d} | {rms(a):7.1f} | {rms(b):7.1f}")
