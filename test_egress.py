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


run("pkill tcpdump >/dev/null 2>&1; rm -f /tmp/eg.txt")
run("nohup timeout 32 tcpdump -U -qnni any 'host 10.208.233.134 or host 10.208.233.197' > /tmp/eg.txt 2>/dev/null & echo ok")
time.sleep(3)

print("==== ping carrier signalling IP FROM THE HOST ====")
print(run("ping -c 3 -W 2 10.208.233.134 2>&1 | tail -4 | sed 's/^/  /'"))

print("==== ping carrier signalling IP FROM THE FREESWITCH CONTAINER ====")
print(run("docker exec skykin-freeswitch ping -c 3 -W 2 10.208.233.134 2>&1 | tail -5 | sed 's/^/  /'"))

print("==== UDP probe from container (source port inside RTP range) ====")
php = (
    '$ctx=stream_context_create(["socket"=>["bindto"=>"0.0.0.0:16400"]]);'
    '$f=@stream_socket_client("udp://10.208.233.134:16400",$e,$s,5,STREAM_CLIENT_CONNECT,$ctx);'
    'if(!$f){echo "  failed: $s\\n";}else{for($i=0;$i<3;$i++){fwrite($f,"skykin-probe");usleep(150000);}'
    'echo "  3 datagrams written\\n";fclose($f);}'
)
print(run('docker exec skykin-web php -r ' + "'" + php + "'" + " 2>&1 | sed 's/^/  /'"))

print("waiting for capture to finish...")
time.sleep(24)
print("==== capture (host ping vs container ping vs container udp) ====")
out = run("cat /tmp/eg.txt 2>&1")
print(out if out.strip() else "  (nothing captured)")
print("  lines: " + run("wc -l < /tmp/eg.txt 2>&1").strip())
c.close()
