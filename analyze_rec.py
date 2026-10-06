import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmd = r'''
docker cp skykin-freeswitch:/var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/a6e6852b-2c25-407b-91dd-c9378e5f1619.wav /tmp/last.wav
python3 - <<'PY'
import wave, struct, math, os
p='/tmp/last.wav'
w=wave.open(p)
ch,sw,sr,n=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes()
print('wav', 'ch',ch,'sw',sw,'sr',sr,'n',n,'sec',round(n/sr,2),'bytes',os.path.getsize(p))
raw=w.readframes(n); w.close()
print('sec | left | right')
for sec in range(int(n/sr)+1):
    start=sec*sr; end=min((sec+1)*sr,n)
    if start>=n: break
    sl=sr_r=0.0; cnt=end-start
    for i in range(start,end):
        o=i*ch*sw
        l=struct.unpack_from('<h', raw, o)[0]
        r=struct.unpack_from('<h', raw, o+2)[0] if ch>1 else 0
        sl += l*l; sr_r += r*r
    print('%3d | %10.1f | %10.1f' % (sec, math.sqrt(sl/cnt), math.sqrt(sr_r/cnt)))
PY
'''
_, o, e = c.exec_command(cmd)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
