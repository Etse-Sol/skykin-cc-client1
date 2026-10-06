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


print("==== which docker network is each container on? ====")
print(run(
    "for x in skykin-freeswitch skykin-web; do echo -n \"  $x: \"; "
    "docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}={{$v.IPAddress}} {{end}}' $x; done"
))

print("==== host forward policy / ufw ====")
print(run("iptables -S FORWARD 2>/dev/null | head -12 | sed 's/^/  /'"))

run("pkill tcpdump >/dev/null 2>&1; rm -f /tmp/np_any.txt /tmp/np_nic.txt /tmp/tcpdump.err")
# 'any' shows the packet both inside the bridge and on the NIC, so we can tell
# whether it was dropped at forwarding or actually NATed and sent.
run(
    "nohup timeout 25 tcpdump -U -qnni any 'udp and net 10.208.233.0/24' "
    "> /tmp/np_any.txt 2>/tmp/tcpdump.err & echo ok"
)
time.sleep(4)
print("  tcpdump running: " + run("pgrep -c tcpdump").strip())
print("  tcpdump stderr: " + run("cat /tmp/tcpdump.err 2>&1").strip())

php = (
    '$t=[["10.208.233.134",16400],["10.208.233.197",16402]];'
    'foreach($t as $d){$p=$d[1];'
    '$ctx=stream_context_create(["socket"=>["bindto"=>"0.0.0.0:".$p]]);'
    '$f=@stream_socket_client("udp://".$d[0].":".$p,$e,$s,5,STREAM_CLIENT_CONNECT,$ctx);'
    'if(!$f){echo "  failed $p: $s\\n";continue;}'
    'for($i=0;$i<3;$i++){fwrite($f,"skykin-probe");usleep(200000);}fclose($f);'
    'echo "  sent 3 datagrams to ".$d[0].":".$p."\\n";}'
)
print("==== probe from skykin-web ====")
print(run('docker exec skykin-web php -r ' + "'" + php + "'" + " 2>&1 | sed 's/^/  /'"))

# Also probe straight from the host, which bypasses Docker NAT entirely. If the
# host packet appears and the container one does not, NAT/forwarding is the wall.
print("==== force a real FreeSWITCH REGISTER so we see genuine trunk traffic ====")
print(run('docker exec skykin-freeswitch fs_cli -x "sofia profile external register SIP" 2>&1 | sed "s/^/  /"'))
time.sleep(14)

print("==== capture result ====")
out = run("cat /tmp/np_any.txt 2>&1")
print(out if out.strip() else "  (nothing captured at all)")
c.close()
