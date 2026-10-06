#!/bin/bash
# On ecs-cc — see who was registered / offered at a specific time.
#   bash agent_at_time.sh
#   bash agent_at_time.sh 2026-09-19 16:00 17:00
#   bash agent_at_time.sh 2026-09-19 17:04 17:05
set -eu
DAY="${1:-2026-09-19}"
T0="${2:-15:00}"
T1="${3:-19:00}"

echo "==== Window: $DAY $T0 -> $T1 ===="

echo
echo "---- FreeSWITCH log (register / offer / softphone fail) ----"
docker exec skykin-freeswitch sh -c "
  grep '$DAY' /var/log/freeswitch/freeswitch.log 2>/dev/null |
  awk -v t0='$DAY $T0' -v t1='$DAY $T1' '
    {
      # line starts with timestamp like 2026-09-19 16:08:12.xxxxxx
      ts = substr(\$0, 1, 16)
      if (ts < t0 || ts > t1) next
      if (\$0 ~ /201@ahununu|202@ahununu|203@ahununu|204@ahununu|205@ahununu|user\/201@|user\/202@|user\/203@|user\/204@|user\/205@/) {
        if (\$0 ~ /REGISTER|Unregister|Registered|expir|softphone_fail|TEMPORARY_FAILURE|queue wait|originate|bridge|Available|Logged Out|On Break|NO_ANSWER|USER_BUSY|DESTINATION_OUT/)
          print
      } else if (\$0 ~ /softphone_fail|queue wait VISIBLE/) {
        print
      }
    }
  ' | tail -n 300
"

echo
echo "---- Counts ----"
docker exec skykin-freeswitch sh -c "
  grep '$DAY' /var/log/freeswitch/freeswitch.log 2>/dev/null |
  awk -v t0='$DAY $T0' -v t1='$DAY $T1' '
    {
      ts = substr(\$0, 1, 16)
      if (ts < t0 || ts > t1) next
      if (\$0 ~ /softphone_fail/) sf++
      if (\$0 ~ /TEMPORARY_FAILURE/) tf++
      if (\$0 ~ /queue wait VISIBLE/) qw++
      if (\$0 ~ /201@ahununu/ && \$0 ~ /REGISTER|Registered/) r1++
      if (\$0 ~ /202@ahununu/ && \$0 ~ /REGISTER|Registered/) r2++
      if (\$0 ~ /203@ahununu/ && \$0 ~ /REGISTER|Registered/) r3++
      if (\$0 ~ /user\/201@ahununu/ && \$0 ~ /originate|bridge/) o1++
      if (\$0 ~ /user\/202@ahununu/ && \$0 ~ /originate|bridge/) o2++
    }
    END {
      print \"softphone_fail=\" (sf+0)
      print \"TEMPORARY_FAILURE=\" (tf+0)
      print \"queue_wait_VISIBLE=\" (qw+0)
      print \"sip_register_201=\" (r1+0)
      print \"sip_register_202=\" (r2+0)
      print \"sip_register_203=\" (r3+0)
      print \"offer_bridge_201=\" (o1+0)
      print \"offer_bridge_202=\" (o2+0)
    }
  '
"

echo
echo "---- CDR in same window ----"
docker exec skykin-postgres psql -U fusionpbx -d fusionpbx -c "
SELECT to_char(start_stamp,'HH24:MI:SS') AS t,
       caller_id_number AS caller,
       billsec,
       hangup_cause,
       CASE
         WHEN coalesce(cc_agent_bridged,'') ~* '/(20[1-5])@' THEN 'ANSWERED'
         WHEN billsec > 0 THEN 'ABANDONED'
         ELSE 'OTHER'
       END AS result,
       coalesce(cc_agent,'') AS cc_agent,
       left(coalesce(last_arg,''),40) AS last_arg
FROM v_xml_cdr
WHERE start_stamp::date = '$DAY'
  AND start_stamp::time >= '$T0:00'
  AND start_stamp::time <  '$T1:59'
  AND direction ILIKE 'inbound'
  AND destination_number LIKE '%116198%'
ORDER BY start_stamp;
"
echo DONE
