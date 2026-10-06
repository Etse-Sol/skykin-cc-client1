import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("196.189.236.140", username="root", password="Pass@1234",
          timeout=25, allow_agent=False, look_for_keys=False)
cmd = r"""
set -e
SRC=/root/skykin-fs-etc/dialplan/default/00_ethio_mobile.xml
if [ -f "$SRC" ]; then
  mv "$SRC" "${SRC}.noload"
  echo moved_to_noload
else
  echo already_gone
fi
docker exec skykin-freeswitch fs_cli -x 'reloadxml'
echo '--- xml_locate ethio ---'
docker exec skykin-freeswitch fs_cli -x 'xml_locate dialplan default ethio_mobile' || true
echo '--- xml_locate skykin_outbound_et_zero ---'
docker exec skykin-freeswitch fs_cli -x 'xml_locate dialplan default skykin_outbound_et_zero' | head -20
echo '--- files ---'
ls -l /root/skykin-fs-etc/dialplan/default/00_ethio* /root/skykin-fs-etc/dialplan/default/00_skykin.xml
"""
_, o, e = c.exec_command(cmd)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
