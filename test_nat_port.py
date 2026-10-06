import sys
import time
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


print("==== tools available inside the freeswitch container ====")
print(run(
    "docker exec skykin-freeswitch sh -c "
    "'for t in nc ncat socat python3 perl; do command -v $t 2>/dev/null; done'"
    " | sed 's/^/  /'"
))

# Capture on the physical NIC: whatever source port shows up here is what the
# carrier sees after Docker's NAT. Port 16400 preserved = symmetric RTP works.
run("pkill tcpdump >/dev/null 2>&1; rm -f /tmp/natport.txt")
run(
    "nohup timeout 30 tcpdump -qnni enp4s3 'udp and net 10.208.233.0/24 and portrange 16000-17000' "
    "> /tmp/natport.txt 2>/dev/null & echo ok"
)
time.sleep(3)

# Send a single 1-byte UDP datagram from source port 16400 out of the container.
print("==== sending UDP probes from a container, bound to source port 16400/16402 ====")
php = (
    '$t=[["10.208.233.134",16400],["10.208.233.197",16402]];'
    'foreach($t as $i=>$d){'
    '$p=$d[1];'
    '$ctx=stream_context_create(["socket"=>["bindto"=>"0.0.0.0:".$p]]);'
    '$f=@stream_socket_client("udp://".$d[0].":".$p,$e,$s,5,STREAM_CLIENT_CONNECT,$ctx);'
    'if(!$f){echo "  bind/connect failed for $p: $s\\n";continue;}'
    'fwrite($f,"skykin-probe-".$p);fclose($f);'
    'echo "  sent to ".$d[0].":".$p." from source port ".$p."\\n";}'
)
print(run('docker exec skykin-web php -r ' + "'" + php + "'" + " 2>&1 | sed 's/^/  /'"))
time.sleep(8)

print("==== what left the server (post-NAT source port) ====")
out = run("cat /tmp/natport.txt 2>&1")
print(out if out.strip() else "  (nothing captured)")
print("  --> if the source port is NOT 16400, Docker rewrote it and the carrier")
print("      receives our RTP from an unexpected port.")
c.close()
