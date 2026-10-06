import array
import io
import math
import sys
import wave
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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


def rms(samples):
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


# The outbound call agent 101 -> +251911227833 placed after the media fix.
UUID = "f244da4b-8fae-4a06-9fd0-26962d2f7a10"
SRC = f"/var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/12/{UUID}.wav"

print("==== fetching recording ====")
print(run(f"docker cp skykin-freeswitch:{SRC} /tmp/an.wav 2>&1 | sed 's/^/  /'"))
print(run("ls -l /tmp/an.wav 2>&1 | sed 's/^/  /'"))

sftp = c.open_sftp()
data = sftp.open("/tmp/an.wav", "rb").read()
sftp.close()
c.close()

w = wave.open(io.BytesIO(data), "rb")
ch, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
raw = w.readframes(frames)
w.close()
print(f"\n  channels={ch} rate={rate} width={width} duration={frames / float(rate):.1f}s")

pcm = array.array("h")
pcm.frombytes(raw[: (len(raw) // 2) * 2])

if ch != 2:
    print(f"  mono file, overall rms={rms(pcm.tolist()):.1f}")
else:
    left = pcm[0::2]
    right = pcm[1::2]
    print(f"  channel A (agent / browser) overall rms = {rms(left.tolist()):8.1f}")
    print(f"  channel B (phone / carrier) overall rms = {rms(right.tolist()):8.1f}")
    print("\n  per-second levels (A=agent, B=phone):")
    print("   sec |    agent |    phone")
    for s in range(0, int(frames / rate)):
        a = left[s * rate:(s + 1) * rate].tolist()
        b = right[s * rate:(s + 1) * rate].tolist()
        if not a:
            break
        print(f"   {s:3d} | {rms(a):8.1f} | {rms(b):8.1f}")
