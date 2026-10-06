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


print("==== latest recordings ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "'ls -lt /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13 "
        "| head -15'"
    )
)

print("==== last outbound / opus / reneg ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E 'Processing 10[0-9].*0902925776|Opus decoder|Opus encoder|uuid_media_reneg|"
        "DTLS state from SETUP to READY|Pre-Answer sofia/external|has been answered|"
        "Remote SDP:|NORMAL_CLEARING|stereo=0' "
        "/var/log/freeswitch/freeswitch.log | tail -80\""
    )
)

print("==== last 102 channels ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E 'New Channel sofia/internal/102|New Channel sofia/external/' "
        "/var/log/freeswitch/freeswitch.log | tail -20\""
    )
)

print("==== gw / agents ====")
print(run("systemctl is-active skykin-ws-sip; journalctl -u skykin-ws-sip -n 20 --no-pager"))
print(
    run(
        "docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'"
    )
)
