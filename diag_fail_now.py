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


def run(cmd, timeout=200):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")


print("==== recs ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "'ls -lt /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13 | head -6'"
    )
)
print("==== last 102 ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E 'Processing 102 <|ignore_early|send_silence|rtcp_audio|"
        "Opus decoder stats|Opus encoder stats|AUDIO RTP \\[sofia/external|"
        "has been answered|NORMAL_CLEARING|AOC|uuid_media' "
        "/var/log/freeswitch/freeswitch.log | tail -50\""
    )
)
