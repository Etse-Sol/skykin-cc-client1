import sys
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


def run(cmd, timeout=120):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


print("==== tone_stream module (needed for ringback tone) ====")
print(run('docker exec skykin-freeswitch fs_cli -x "show modules" 2>&1 | grep -aiE "tone_stream|dptools|sndfile" | sed "s/^/  /"'))

print("==== does the echo test extension exist (9196)? ====")
print(run(r"""docker exec skykin-freeswitch sh -c 'grep -a -A 6 "skykin_echo_test" /etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml' | sed 's/^/  /' """))

print("==== internal profile: WebRTC media settings ====")
print(run(r"""docker exec skykin-freeswitch grep -aE "ext-rtp-ip|ext-sip-ip|rtp-ip|dtls|DTLS|apply-candidate-acl|rtcp" /etc/freeswitch/sip_profiles/internal.xml | sed 's/^/  /' """))

print("==== channels right now ====")
print(run('docker exec skykin-freeswitch fs_cli -x "show channels count" 2>&1 | sed "s/^/  /"'))
c.close()
