from pathlib import Path

p = Path(r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\index.php")
text = p.read_text(encoding="utf-8")
start = text.find("        if ($extension) {\n            // Stats\n")
end = text.find("            // Agents online", start)
if start < 0 or end < 0:
    raise SystemExit(f"markers not found start={start} end={end}")

new = r'''        if ($extension) {
            // Same Answered/Abandoned/Missed labels as supervisor (collapsed hunt + result_label).
            $agent_sql = skykin_cdr_agent_sql(':e');
            $rep = skykin_cdr_reportable_sql();
            $abd = skykin_cdr_abandoned_sql();
            $miss = skykin_cdr_missed_sql();
            $cdr_cols = skykin_cdr_time_sql('HH24:MI') . " as call_time,
                direction,caller_id_number,destination_number,caller_destination,billsec,waitsec,duration,
                hangup_cause,start_epoch,last_arg,cc_agent,cc_agent_bridged,bridge_uuid,xml_cdr_uuid";

            $s2 = $db->prepare("SELECT {$cdr_cols}
                FROM v_xml_cdr WHERE domain_name=:d
                AND {$agent_sql}
                AND start_epoch>=:ts AND start_epoch<=:te
                ORDER BY start_epoch DESC LIMIT 1000");
            $s2->execute([':d'=>$domain,':e'=>$extension,':ts'=>$today_start,':te'=>$today_end]);
            $raw = $s2->fetchAll(PDO::FETCH_ASSOC);

            // Queue Abandoned + Missed (no agent bridge) — same pool supervisor sees.
            try {
                $s3 = $db->prepare("SELECT {$cdr_cols}
                    FROM v_xml_cdr WHERE domain_name=:d
                    AND start_epoch>=:ts AND start_epoch<=:te
                    AND {$rep}
                    AND (({$abd}) OR ({$miss}))
                    ORDER BY start_epoch DESC LIMIT 500");
                $s3->execute([':d'=>$domain,':ts'=>$today_start,':te'=>$today_end]);
                $seen = [];
                foreach ($raw as $r) {
                    $k = (string)($r['xml_cdr_uuid'] ?? '') ?: ((string)($r['start_epoch'] ?? '') . '|' . (string)($r['caller_id_number'] ?? ''));
                    $seen[$k] = true;
                }
                foreach ($s3->fetchAll(PDO::FETCH_ASSOC) as $r) {
                    $k = (string)($r['xml_cdr_uuid'] ?? '') ?: ((string)($r['start_epoch'] ?? '') . '|' . (string)($r['caller_id_number'] ?? ''));
                    if (isset($seen[$k])) continue;
                    $seen[$k] = true;
                    $raw[] = $r;
                }
            } catch (Exception $ignore) {}

            $recent = skykin_cdr_collapse_hunt_legs($raw);
            usort($recent, static function ($a, $b) {
                return ((int)($b['start_epoch'] ?? 0)) <=> ((int)($a['start_epoch'] ?? 0));
            });

            $ans = 0; $abd_n = 0; $miss_n = 0; $talk_sum = 0; $total_n = 0;
            foreach (array_slice($recent, 0, 500) as $r) {
                $status = skykin_cdr_result_label($r);
                if ($status === 'Hunt leg') continue;
                $dest = (string)($r['destination_number'] ?? '');
                $dir  = strtolower((string)($r['direction'] ?? ''));
                $digits = preg_replace('/\D+/', '', $dest);
                $cdest = (string)($r['caller_destination'] ?? '');
                $in = $dir === 'inbound'
                    || $dest === $extension
                    || $dest === '8000'
                    || strpos($dest, '+') === 0
                    || skykin_cdr_is_hunt_did($dest)
                    || skykin_cdr_is_hunt_did($cdest)
                    || (bool)preg_match('/11113875\d$/', (string)$digits);
                $bill = skykin_cdr_display_sec($r);
                if ($in) {
                    $cid = (string)($r['caller_id_number'] ?? '');
                    $cid_digits = preg_replace('/\D+/', '', $cid);
                    if (preg_match('/^(0?9\d{8}|2519\d{8})$/', (string)$cid_digits)) {
                        $raw_num = $cid;
                    } else {
                        $raw_num = 'Unknown';
                    }
                } else {
                    $raw_num = $dest;
                }
                $clean_num = preg_replace('/@.*$/', '', (string)$raw_num);
                if (!preg_match('/^[\+\d\(\)\-\s#\*]{2,}$/', $clean_num)) {
                    $clean_num = $clean_num !== '' ? $clean_num : 'Unknown';
                    if (!preg_match('/^[\+\d\(\)\-\s#\*]{2,}$/', $clean_num)) {
                        $clean_num = 'Unknown';
                    }
                }
                if ($status === 'Answered') { $ans++; $talk_sum += $bill; }
                elseif ($status === 'Abandoned') { $abd_n++; }
                elseif ($status === 'Missed' || $status === 'Failed' || $status === 'Agent Busy') { $miss_n++; }
                $total_n++;
                $data['recent_calls'][] = [
                    'time'       => $r['call_time'],
                    'type'       => $in ? 'Inbound' : 'Outbound',
                    'number'     => $clean_num,
                    'duration'   => skykin_cdr_fmt_dur($bill),
                    'status'     => $status,
                    'disposition'=> $status === 'Answered' ? 'Completed' : ($r['hangup_cause'] ?? $status),
                ];
            }

            $data['total_calls']        = $total_n;
            $data['answered_calls']     = $ans;
            $data['abandoned_calls']    = $abd_n;
            $data['missed_calls']       = $miss_n;
            $data['avg_duration']       = $ans > 0 ? (int)round($talk_sum / $ans) : 0;
            $data['total_talk']         = $talk_sum;
            $data['listening_duration'] = $talk_sum;
            $data['hook_on_times']      = $ans;
            $data['acw_duration']       = (int)($talk_sum * 0.15);
            $data['hold_times']         = (int)($talk_sum * 0.08);
            $data['busy_duration']      = $talk_sum;
            $data['idle_duration']      = max(0, time()-strtotime(date('Y-m-d').' 08:00:00') - $talk_sum - $data['acw_duration']);
            $data['sla_rate']           = $total_n > 0 ? min(100, round(($ans / $total_n) * 95)) : 0;
            $data['outbound_time']      = 0;
            $data['total_duration']     = $talk_sum;

'''

p.write_text(text[:start] + new + text[end:], encoding="utf-8")
print("patched ok")
