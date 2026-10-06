import re
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


def run(cmd, timeout=200):
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    return out.read().decode(errors="replace")


print("==== capture file so far ====")
print(run("wc -l /tmp/audio_test.txt 2>&1 | sed 's/^/  /'"))
print(run("pgrep -c tcpdump 2>&1 | sed 's/^/  tcpdump still running: /'"))

# Pull the raw CDR XML for the most recent outbound calls. FreeSWITCH records
# per-leg RTP counters there, which settles the direction question without a call.
q = (
    "SELECT xml_cdr_uuid, start_stamp, destination_number, billsec, hangup_cause "
    "FROM v_xml_cdr WHERE destination_number ~ '^(0|9|\\+?251)[0-9]{6,}$' "
    "ORDER BY start_stamp DESC LIMIT 6;"
)
print("==== recent outbound CDRs ====")
print(run(
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -A -F' | ' -c \"" + q + "\" 2>&1 | sed 's/^/  /'"
))

# Grab the XML blob of the newest one and pull the audio counters out of it.
uuid_out = run(
    "docker exec skykin-db psql -U fusionpbx -d fusionpbx -t -A -c "
    "\"SELECT xml_cdr_uuid FROM v_xml_cdr WHERE destination_number ~ '^(0|9|\\+?251)[0-9]{6,}$' "
    "ORDER BY start_stamp DESC LIMIT 1;\" 2>&1"
).strip()
print("newest outbound uuid: " + uuid_out)

if uuid_out and "ERROR" not in uuid_out:
    blob = run(
        "docker exec skykin-db psql -U fusionpbx -d fusionpbx -t -A -c "
        f"\"SELECT xml FROM v_xml_cdr WHERE xml_cdr_uuid='{uuid_out}';\" 2>&1",
        timeout=200,
    )
    print("  xml length: %d" % len(blob))
    keys = [
        "rtp_audio_in_raw_bytes", "rtp_audio_out_raw_bytes",
        "rtp_audio_in_media_packet_count", "rtp_audio_out_media_packet_count",
        "rtp_audio_in_packet_count", "rtp_audio_out_packet_count",
        "rtp_audio_in_skip_packet_count", "rtp_audio_in_jitter_packet_count",
        "read_codec_name", "write_codec_name",
        "remote_media_ip", "remote_media_port", "local_media_ip", "local_media_port",
        "rtp_use_codec_name", "sip_local_sdp_str", "endpoint_disposition",
    ]
    for k in keys:
        for m in re.findall(r"<%s>(.*?)</%s>" % (k, k), blob, re.S)[:2]:
            v = m.strip()
            if len(v) > 300:
                v = v[:300] + "..."
            print(f"  {k} = {v}")
c.close()
