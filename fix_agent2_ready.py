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

xml = r"""python3 - <<'PY'
from pathlib import Path
p = Path("/root/skykin-fs-etc/autoload_configs/callcenter.conf.xml")
p.write_text('''<configuration name="callcenter.conf" description="CallCenter">
  <settings>
    <param name="odbc-dsn" value=""/>
  </settings>
  <queues>
    <queue name="8000@client1.skykin.local">
      <param name="strategy" value="ring-all"/>
      <param name="moh-sound" value=""/>
      <param name="time-base-score" value="system"/>
      <param name="max-wait-time" value="0"/>
      <param name="max-wait-time-with-no-agent" value="0"/>
      <param name="max-wait-time-with-no-agent-time-reached" value="5"/>
      <param name="tier-rules-apply" value="false"/>
      <param name="tier-rule-wait-second" value="300"/>
      <param name="tier-rule-wait-multiply-level" value="true"/>
      <param name="tier-rule-no-agent-no-wait" value="false"/>
      <param name="discard-abandoned-after" value="60"/>
      <param name="abandoned-resume-allowed" value="false"/>
    </queue>
  </queues>
  <agents>
    <agent name="64c5f323-cd40-48ef-a97f-22d546be8b57" type="callback" contact="[leg_timeout=30]user/101@client1.skykin.local" status="Logged Out" max-no-answer="999" wrap-up-time="10" reject-delay-time="10" busy-delay-time="60"/>
    <agent name="031ab55a-74f4-4c4a-9252-faaa4a1f4e5e" type="callback" contact="[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,rtp_advertise_ip=196.189.236.140,include_external_ip=true]user/102@client1.skykin.local" status="Available" max-no-answer="999" wrap-up-time="10" reject-delay-time="10" busy-delay-time="60"/>
    <agent name="cd794b4f-f54e-4110-ba5d-537a034c243c" type="callback" contact="[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,rtp_advertise_ip=196.189.236.140,include_external_ip=true]user/103@client1.skykin.local" status="Available" max-no-answer="999" wrap-up-time="10" reject-delay-time="10" busy-delay-time="60"/>
    <agent name="b3867d46-795b-47bd-a933-d90d16f10a75" type="callback" contact="[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,rtp_advertise_ip=196.189.236.140,include_external_ip=true]user/104@client1.skykin.local" status="Logged Out" max-no-answer="999" wrap-up-time="10" reject-delay-time="10" busy-delay-time="60"/>
  </agents>
  <tiers>
    <tier queue="8000@client1.skykin.local" agent="64c5f323-cd40-48ef-a97f-22d546be8b57" state="Ready" level="1" position="1"/>
    <tier queue="8000@client1.skykin.local" agent="031ab55a-74f4-4c4a-9252-faaa4a1f4e5e" state="Ready" level="1" position="1"/>
    <tier queue="8000@client1.skykin.local" agent="cd794b4f-f54e-4110-ba5d-537a034c243c" state="Ready" level="1" position="1"/>
    <tier queue="8000@client1.skykin.local" agent="b3867d46-795b-47bd-a933-d90d16f10a75" state="Ready" level="1" position="1"/>
  </tiers>
</configuration>
''')
print("wrote callcenter.conf.xml")
PY
"""

web = "[leg_timeout=30,media_webrtc=true,rtp_secure_media=optional,rtp_advertise_ip=196.189.236.140,include_external_ip=true]"
cmds = f"""
{xml}
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c \\
  "UPDATE v_call_center_agents SET agent_contact = '{web}user/102@client1.skykin.local', agent_max_no_answer = 999, agent_status = 'Available' WHERE call_center_agent_uuid = '031ab55a-74f4-4c4a-9252-faaa4a1f4e5e';
   UPDATE v_call_center_agents SET agent_contact = '{web}user/103@client1.skykin.local', agent_max_no_answer = 999 WHERE call_center_agent_uuid = 'cd794b4f-f54e-4110-ba5d-537a034c243c';
   UPDATE v_call_center_agents SET agent_status = 'Logged Out' WHERE call_center_agent_uuid = '64c5f323-cd40-48ef-a97f-22d546be8b57';"

docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set contact 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e '{web}user/102@client1.skykin.local'"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set max_no_answer 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e 999"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set no_answer_count 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e 0"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set status 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e Available"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set state 031ab55a-74f4-4c4a-9252-faaa4a1f4e5e Waiting"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set contact cd794b4f-f54e-4110-ba5d-537a034c243c '{web}user/103@client1.skykin.local'"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set max_no_answer cd794b4f-f54e-4110-ba5d-537a034c243c 999"
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent set status 64c5f323-cd40-48ef-a97f-22d546be8b57 'Logged Out'"
echo '==== agents ===='
docker exec skykin-freeswitch fs_cli -x "callcenter_config agent list" | cut -d'|' -f1,5,6,7
"""
_, o, e = c.exec_command(cmds)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
