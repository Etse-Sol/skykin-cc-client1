import array
import io
import math
import sys
import wave
import paramiko


def levels(samples):
    """RMS and peak of a list of 16-bit samples."""
    if not samples:
        return 0.0, 0
    total = 0
    peak = 0
    for s in samples:
        total += s * s
        a = -s if s < 0 else s
        if a > peak:
            peak = a
    return math.sqrt(total / len(samples)), peak

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


def run(cmd, timeout=200):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


print("==== what the 3-min capture saw (carrier UDP) ====")
print(run("cat /tmp/audio_test.txt 2>&1 | sed 's/^/  /'"))

# The two calls that actually connected. record_stereo puts the agent on one
# channel and the carrier on the other, so silence on a single channel points at
# the direction that failed.
for u in ("b6201c5c-28e0-4d42-9aec-875d769758d7", "2afdf127-a6a3-4505-b70a-51067f170c24"):
    print(f"\n==== recording for {u} ====")
    found = run(
        "docker exec skykin-freeswitch sh -c "
        f"'find /var/lib/freeswitch/recordings -name \"{u}*\" -printf \"%s %p\\n\" 2>/dev/null'"
    ).strip()
    print("  " + (found.replace("\n", "\n  ") if found else "(no file on disk)"))
    if not found:
        continue
    path = found.splitlines()[0].split(" ", 1)[1].strip()

    # Copy out of the container to the host, then read it over SFTP.
    run(f"docker cp skykin-freeswitch:{path} /tmp/rec_{u}.wav 2>&1")
    sftp = c.open_sftp()
    try:
        data = sftp.open(f"/tmp/rec_{u}.wav", "rb").read()
    except Exception as e:  # noqa: BLE001
        print(f"  could not fetch: {e}")
        sftp.close()
        continue
    sftp.close()

    try:
        w = wave.open(io.BytesIO(data), "rb")
    except Exception as e:  # noqa: BLE001
        print(f"  not a readable wav: {e}")
        continue
    ch, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    raw = w.readframes(frames)
    w.close()
    dur = frames / float(rate or 1)
    print(f"  channels={ch} rate={rate} width={width} frames={frames} duration={dur:.1f}s")
    if width != 2:
        print("  unexpected sample width, skipping level analysis")
        continue

    pcm = array.array("h")
    pcm.frombytes(raw[: (len(raw) // 2) * 2])
    if ch == 2:
        a_rms, a_peak = levels(pcm[0::2])
        b_rms, b_peak = levels(pcm[1::2])
        print(f"  channel A (agent side)   rms={a_rms:8.1f}  peak={a_peak:6d}")
        print(f"  channel B (carrier side) rms={b_rms:8.1f}  peak={b_peak:6d}")
    else:
        m_rms, m_peak = levels(pcm)
        print(f"  mono rms={m_rms:8.1f} peak={m_peak:6d}")
c.close()
