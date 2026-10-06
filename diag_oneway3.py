import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
analyze = r'''
python3 - <<'PY'
import wave, struct, math, os
p='/var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/a6e6852b-2c25-407b-91dd-c9378e5f1619.wav'
w=wave.open(p)
ch,sw,sr,n=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes()
print('wav', ch, sw, sr, n, 'sec', round(n/sr,2), 'bytes', os.path.getsize(p))
raw=w.readframes(n)
w.close()
# int16 stereo
frames=n
# per-second RMS per channel
print('sec | left(agent?) | right(phone?)')
for sec in range(int(n/sr)+1):
    start=sec*sr
    end=min((sec+1)*sr, n)
    if start>=n: break
    sl=sr_l=0.0
    sr_r=0.0
    cnt=end-start
    for i in range(start,end):
        o=i*ch*sw
        l=struct.unpack_from('<h', raw, o)[0]
        r=struct.unpack_from('<h', raw, o+2)[0] if ch>1 else 0
        sl += l*l
        sr_r += r*r
    rms_l=math.sqrt(sl/cnt) if cnt else 0
    rms_r=math.sqrt(sr_r/cnt) if cnt else 0
    print(f'{sec:3d} | {rms_l:10.1f} | {rms_r:10.1f}')
PY
'''
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n 'a6e6852b\|8931eaab' /var/log/freeswitch/freeswitch.log | grep -iE 'RTP |stats|bytes|jitter|loss|SKIP|auto.?adj|Auto Changing|send|recv|dtls|BYE|183|200' | tail -80" """,
    "docker exec skykin-freeswitch sh -c " + repr(analyze),
    r"""docker exec skykin-freeswitch sh -c "sed -n '222608,222620p' /var/log/freeswitch/freeswitch.log" """,
]
for cmd in cmds:
    print("====", cmd[:90])
    _, o, e = c.exec_command(cmd)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    print(out[-15000:] if len(out) > 15000 else out)
c.close()
