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
        "'ls -lt /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13 | head -8'"
    )
)
print("==== last 102 processing / hangup / opus / dtls / ignore ====")
print(
    run(
        "docker exec skykin-freeswitch sh -c "
        "\"grep -E 'Processing 102|ignore_early|pre_answer|DTLS state from SETUP|"
        "Opus decoder|Opus encoder stats|has been answered|NORMAL_CLEARING|"
        "Originate Resulted|Hangup sofia/internal/102' "
        "/var/log/freeswitch/freeswitch.log | tail -60\""
    )
)
print("==== client_log ====")
print(
    run(
        "ls -lt /var/log /opt/call-center-deployement/call-center/log 2>/dev/null | head; "
        "grep -l client_log /opt/call-center-deployement/call-center/app/agent_dashboard/*.php | head; "
        "tail -30 /var/log/nginx/access.log 2>/dev/null | grep agent_dashboard | tail -10"
    )
)
print("==== index on web ====")
print(
    run(
        "grep -n '20260813\\|mediaStream\\|ignore_early' "
        "/opt/call-center-deployement/call-center/app/agent_dashboard/index.php | head -20"
    )
)
