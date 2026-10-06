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


def run(cmd, timeout=250):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


print("==== what user does FreeSWITCH run as? ====")
print(run("docker exec skykin-freeswitch sh -c 'ps -o user,group,comm -p 1; id' 2>&1 | sed 's/^/  /'"))

print("==== recordings tree ownership ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'ls -ld /var/lib/freeswitch/recordings /var/lib/freeswitch/recordings/client1.skykin.local "
    "/var/lib/freeswitch/recordings/client1.skykin.local/archive' 2>&1 | sed 's/^/  /'"
))

print("==== can FreeSWITCH actually create today's archive dir? ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'D=/var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/12; "
    "mkdir -p $D 2>&1 && touch $D/.probe 2>&1 && echo \"  writable: $D\" && rm -f $D/.probe' 2>&1 | sed 's/^/  /'"
))

print("==== granting write access so record_session can save calls ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'chmod -R u+rwX,g+rwX /var/lib/freeswitch/recordings && "
    "chown -R 0:33 /var/lib/freeswitch/recordings && "
    "find /var/lib/freeswitch/recordings -type d -exec chmod g+s {} + && "
    "ls -ld /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/12' 2>&1 | sed 's/^/  /'"
))

print("==== a-leg (browser) codec + media info from the debug log ====")
print(run(
    "docker logs --since 12m skykin-freeswitch 2>&1 | "
    "grep -aiE 'Codec Activity|Set Codec|Audio Codec|opus|read_codec|write_codec|transcod' "
    "| tail -25 | sed 's/^/  /'"
) or "  (nothing logged)")

print("==== is mod_opus loaded (needed to decode the browser's audio)? ====")
print(run(
    'docker exec skykin-freeswitch fs_cli -x "show modules" 2>&1 '
    "| grep -aiE 'opus|g722|mod_spandsp' | head | sed 's/^/  /'"
))
c.close()
