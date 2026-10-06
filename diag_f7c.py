import array
import io
import math
import sys
import wave
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UUID = "f7c36f08-fd03-434b-826a-ccb571aa21ed"
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


print("==== codecs / route / sip gw ====")
print(run("docker exec skykin-freeswitch fs_cli -x 'show codec' | grep -iE 'PCMA|PCMU|AMR|opus|G729'"))
print(run("ip route get 10.208.233.197; ip -4 addr show enp4s3 | head -4"))
print(run("cat /root/skykin-fs-etc/sip_profiles/external/SIP.xml"))
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        f"\"awk '/{UUID}|2917af7f-b88b-4e63-b140-cb0e7a51ff1f/{{p=1}} p' "
        "/var/log/freeswitch/freeswitch.log | "
        "grep -A 20 'Local SDP:\\|Remote SDP:' | head -80\""
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
pcm = array.array("h")
pcm.frombytes(raw[: (len(raw) // 2) * 2])
left, right = pcm[0::2], pcm[1::2]
print(f"\nch0(agent)={rms(left.tolist()):.1f} ch1(phone)={rms(right.tolist()):.1f} dur={frames/rate:.1f}s")
print("sec |    agent |    phone")
for s in range(0, int(frames / rate)):
    a = left[s * rate : (s + 1) * rate].tolist()
    b = right[s * rate : (s + 1) * rate].tolist()
    print(f"{s:3d} | {rms(a):8.1f} | {rms(b):8.1f}")
