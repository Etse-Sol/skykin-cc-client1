import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmds = [
    r"""
docker exec skykin-freeswitch sh -c '
for u in 5bfbd706-49ea-4670-8b39-0c10132f48d0 ef927091-bbbb-4652-b4ad-5fe7e4d43df1 047003ea-e017-4749-8f8d-f76cf0ada1b9; do
  echo "==== $u ===="
  grep -n "$u" /var/log/freeswitch/freeswitch.log | grep -iE "New Channel|answered|Hangup|AUDIO RTP|opus|PCMA|DTLS|Secure RTP|BRIDGE|Agent |callcenter|Ring-Ready|USER_NOT" | tail -25
done
'
""",
    r"""
docker exec skykin-freeswitch sh -c '
cp /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/5bfbd706-49ea-4670-8b39-0c10132f48d0.wav /tmp/a.wav
cp /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/ef927091-bbbb-4652-b4ad-5fe7e4d43df1.wav /tmp/b.wav
cp /var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/047003ea-e017-4749-8f8d-f76cf0ada1b9.wav /tmp/c.wav
'
python3 - <<'PY'
import wave, struct, math, os
for name in ['/tmp/a.wav','/tmp/b.wav','/tmp/c.wav']:
    w=wave.open(name)
    ch,sw,sr,n=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes()
    print('FILE', name, 'ch',ch,'sr',sr,'sec',round(n/sr,2))
    raw=w.readframes(n); w.close()
    print('sec | ch0 | ch1')
    for sec in range(min(int(n/sr)+1, 40)):
        start=sec*sr; end=min((sec+1)*sr,n)
        if start>=n: break
        s0=s1=0.0; cnt=end-start
        for i in range(start,end):
            o=i*ch*sw
            a=struct.unpack_from('<h', raw, o)[0]
            b=struct.unpack_from('<h', raw, o+2)[0] if ch>1 else 0
            s0 += a*a; s1 += b*b
        print('%3d | %10.1f | %10.1f' % (sec, math.sqrt(s0/cnt), math.sqrt(s1/cnt)))
    print()
PY
""",
    r"""docker exec skykin-freeswitch fs_cli -x 'sofia status profile internal reg'""",
    r"""docker exec skykin-freeswitch fs_cli -x 'callcenter_config agent list' | cut -d'|' -f1,5,6,7""",
]
for cmd in cmds:
    print("====", cmd[:70])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
