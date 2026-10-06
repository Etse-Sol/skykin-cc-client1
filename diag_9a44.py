import array
import io
import math
import sys
import wave
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UUID = "9a441726-d05c-4de6-add5-56ac682cd588"
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


print(
    run(
        "docker exec skykin-freeswitch sh -c "
        f"\"grep -E '{UUID}|7cfbf46d-5866-4f5d-b731-58f5e7d8112b' "
        "/var/log/freeswitch/freeswitch.log | "
        "grep -iE 'AUDIO RTP|Remote SDP|Local SDP|Set Codec|rtcp|AOC|aoc|"
        "resampler|answered|Pre-Answer|ignore_early' | head -80\""
    )
)
src = (
    "/var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/"
    f"{UUID}.wav"
)
run(f"docker cp skykin-freeswitch:{src} /tmp/an.wav")
sftp = c.open_sftp()
data = sftp.open("/tmp/an.wav", "rb").read()
sftp.close()
c.close()


def rms(samples):
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


w = wave.open(io.BytesIO(data), "rb")
ch, rate, frames = w.getnchannels(), w.getframerate(), w.getnframes()
raw = w.readframes(frames)
w.close()
print(f"\nchannels={ch} rate={rate} duration={frames / float(rate):.1f}s")
pcm = array.array("h")
pcm.frombytes(raw[: (len(raw) // 2) * 2])
left, right = pcm[0::2], pcm[1::2]
print(f"ch0(agent) rms={rms(left.tolist()):.1f}  ch1(phone) rms={rms(right.tolist()):.1f}")
print("sec |    agent |    phone")
for s in range(0, int(frames / rate)):
    a = left[s * rate : (s + 1) * rate].tolist()
    b = right[s * rate : (s + 1) * rate].tolist()
    print(f"{s:3d} | {rms(a):8.1f} | {rms(b):8.1f}")
