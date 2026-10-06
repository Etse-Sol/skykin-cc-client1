import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
py = r'''
import wave, struct, math
w=wave.open("/tmp/ms.wav")
ch,sw,sr,n=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes()
print("wav","ch",ch,"sr",sr,"sec",round(n/sr,2))
raw=w.readframes(n); w.close()
print("sec | ch0 | ch1")
for sec in range(int(n/sr)+1):
    start=sec*sr; end=min((sec+1)*sr,n)
    if start>=n: break
    s0=s1=0.0; cnt=end-start
    for i in range(start,end):
        o=i*ch*sw
        a=struct.unpack_from("<h", raw, o)[0]
        b=struct.unpack_from("<h", raw, o+2)[0] if ch>1 else 0
        s0 += a*a; s1 += b*b
    print("%3d | %12.1f | %12.1f" % (sec, math.sqrt(s0/cnt), math.sqrt(s1/cnt)))
'''
sftp = c.open_sftp()
with sftp.file("/tmp/an_ms.py", "w") as f:
    f.write(py)
sftp.close()
cmds = [
    r"""docker exec skykin-freeswitch sh -c "grep -n '45665269\\|2af4a506' /var/log/freeswitch/freeswitch.log | grep -iE 'AUDIO RTP|codec|PCMA|opus|DTLS|Secure|bridge|answered|Hangup|sdp|c=IN|m=audio|advertise'" """,
    "docker cp skykin-freeswitch:/var/lib/freeswitch/recordings/client1.skykin.local/archive/2026/Aug/13/45665269-aaae-457f-ad8e-068a4a97462b.wav /tmp/ms.wav && python3 /tmp/an_ms.py",
]
for cmd in cmds:
    print("====", cmd[:80])
    _, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
