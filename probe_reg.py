import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmd = r"""
python3 - <<'PY'
import socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(('10.0.0.93',0))
s.settimeout(3)
host,port=s.getsockname()
msg=('REGISTER sip:client1.skykin.local SIP/2.0\r\n'
     'Via: SIP/2.0/UDP 10.0.0.93:%s;branch=z9hG4bKprobe2;rport\r\n'
     'From: <sip:102@client1.skykin.local>;tag=probe2\r\n'
     'To: <sip:102@client1.skykin.local>\r\n'
     'Call-ID: probe-reg-2\r\n'
     'CSeq: 1 REGISTER\r\n'
     'Contact: <sip:102@10.0.0.93:%s;transport=udp>\r\n'
     'Expires: 60\r\n'
     'Content-Length: 0\r\n\r\n')%(port,port)
s.sendto(msg.encode(),('10.0.0.93',5060))
try:
    data,addr=s.recvfrom(65535)
    print('GOT',addr,data.split(b'\r\n',1)[0])
except Exception as e:
    print('NO_REPLY',type(e).__name__,e)
s.close()
PY
python3 --version
"""
_, o, e = c.exec_command(cmd)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
