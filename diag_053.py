import array
import io
import math
import sys
import wave
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UUID = "053ffad5-5a33-4e57-a672-cea6b5674b64"
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
        f"\"grep '{UUID}' /var/log/freeswitch/freeswitch.log | "
        "grep -iE 'DTLS|SRTP|ICE|stun|Discard|Invalid|error|Set Codec|AUDIO RTP|"
        "Auto Changing|READY|answered|resampler|read_codec' | tail -60\""
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
ch, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
raw = w.readframes(frames)
w.close()
print(f"channels={ch} rate={rate} duration={frames / float(rate):.1f}s")
pcm = array.array("h")
pcm.frombytes(raw[: (len(raw) // 2) * 2])
left, right = pcm[0::2], pcm[1::2]
print(f"ch0 rms={rms(left.tolist()):.1f} ch1 rms={rms(right.tolist()):.1f}")
print("sec |     ch0 |     ch1")
for s in range(0, int(frames / rate)):
    a = left[s * rate : (s + 1) * rate].tolist()
    b = right[s * rate : (s + 1) * rate].tolist()
    print(f"{s:3d} | {rms(a):7.1f} | {rms(b):7.1f}")
