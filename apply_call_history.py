#!/usr/bin/env python3
"""Fix All Call History on ecs-cc: Agent column, drop Unknown WebRTC rows, infer direction.

Run as root on ecs-cc:

  python3 /tmp/apply_call_history.py
"""
from pathlib import Path
import subprocess
import re
import sys

P = Path("/opt/skykin/app/app/agent_dashboard/supervisor.php")
if not P.is_file():
    sys.exit("missing " + str(P))

t = P.read_text(encoding="utf-8")

OLD_API = r"""        $where = "domain_name=:d AND start_epoch>=:ts AND start_epoch<=:te";
        $params = [':d'=>$domain_,':ts'=>$ts,':te'=>$te];
        if ($search) { $where.=" AND (caller_id_number LIKE :q OR destination_number LIKE :q)"; $params[':q']='%'.$search.'%'; }
        $s = $db->prepare("SELECT to_char(to_timestamp(start_epoch),'YYYY-MM-DD HH24:MI') as call_time,
            caller_id_number, destination_number, direction, billsec, duration, hangup_cause
            FROM v_xml_cdr WHERE $where ORDER BY start_epoch DESC LIMIT 500");
        $s->execute($params);
        $rows = [];
        foreach($s->fetchAll(PDO::FETCH_ASSOC) as $r) {
            $b=(int)$r['billsec'];
            // Resolve SIP usernames to extension numbers
            $caller = preg_replace('/@.*$/', '', $r['caller_id_number']);
            $dest   = preg_replace('/@.*$/', '', $r['destination_number']);
            if (!preg_match('/^[\+\d\(\)\-\s#\*]{2,}$/', $caller))
                $caller = $uname_ext[strtolower($caller)] ?? 'Unknown';
            if (!preg_match('/^[\+\d\(\)\-\s#\*]{2,}$/', $dest))
                $dest   = $uname_ext[strtolower($dest)]   ?? 'Unknown';
            $rows[] = ['time'=>$r['call_time'],'caller'=>$caller,
                'destination'=>$dest,'direction'=>$r['direction'],
                'duration'=>floor($b/60).':'.str_pad($b%60,2,'0',STR_PAD_LEFT),
                'status'=>$b>0?'Answered':'Missed','cause'=>$r['hangup_cause']??''];
        }"""

NEW_API = r"""        $where = "domain_name=:d AND start_epoch>=:ts AND start_epoch<=:te AND (leg IS NULL OR LOWER(TRIM(leg::text)) <> 'b')";
        $params = [':d'=>$domain_,':ts'=>$ts,':te'=>$te];
        if ($search) { $where.=" AND (caller_id_number LIKE :q OR destination_number LIKE :q OR caller_destination LIKE :q OR last_arg LIKE :q)"; $params[':q']='%'.$search.'%'; }
        $s = $db->prepare("SELECT to_char(to_timestamp(start_epoch),'YYYY-MM-DD HH24:MI') as call_time,
            caller_id_number, destination_number, caller_destination, direction, billsec, duration,
            hangup_cause, last_arg, cc_agent, cc_agent_bridged
            FROM v_xml_cdr WHERE $where ORDER BY start_epoch DESC LIMIT 500");
        try {
            $s->execute($params);
        } catch (Exception $legErr) {
            $where = "domain_name=:d AND start_epoch>=:ts AND start_epoch<=:te";
            $params = [':d'=>$domain_,':ts'=>$ts,':te'=>$te];
            if ($search) { $where.=" AND (caller_id_number LIKE :q OR destination_number LIKE :q)"; $params[':q']='%'.$search.'%'; }
            $s = $db->prepare("SELECT to_char(to_timestamp(start_epoch),'YYYY-MM-DD HH24:MI') as call_time,
                caller_id_number, destination_number, caller_destination, direction, billsec, duration,
                hangup_cause, last_arg, cc_agent, cc_agent_bridged
                FROM v_xml_cdr WHERE $where ORDER BY start_epoch DESC LIMIT 500");
            $s->execute($params);
        }
        $rows = [];
        $agent_label = [];
        try {
            $sa = $db->prepare("SELECT agent_name, agent_id, agent_contact FROM v_call_center_agents ca
                JOIN v_domains d ON d.domain_uuid=ca.domain_uuid WHERE d.domain_name=:d");
            $sa->execute([':d'=>$domain_]);
            foreach ($sa->fetchAll(PDO::FETCH_ASSOC) as $ag) {
                $lab = trim((string)($ag['agent_name'] ?? ''));
                if ($ag['agent_id'] !== '' && $ag['agent_id'] !== null) {
                    $agent_label[(string)$ag['agent_id']] = $lab !== '' ? $lab : (string)$ag['agent_id'];
                }
                if (preg_match('/(?:user\/)?(\d+)@/i', (string)($ag['agent_contact'] ?? ''), $m)) {
                    $agent_label[$m[1]] = $lab !== '' ? $lab.' ('.$m[1].')' : $m[1];
                }
            }
        } catch (Exception $ignore) {}
        foreach($s->fetchAll(PDO::FETCH_ASSOC) as $r) {
            $b=(int)$r['billsec'];
            $caller = preg_replace('/@.*$/', '', (string)$r['caller_id_number']);
            $dest   = preg_replace('/@.*$/', '', (string)$r['destination_number']);
            $cdest  = preg_replace('/@.*$/', '', (string)($r['caller_destination'] ?? ''));
            $arg    = (string)($r['last_arg'] ?? '');
            $cc     = (string)($r['cc_agent'] ?? '');
            if (preg_match('/(?:user\/)?(\d{2,4})@/', $cc, $m)) $cc = $m[1];
            if (!preg_match('/^[\+\d\(\)\-\s#\*]{2,}$/', $caller))
                $caller = $uname_ext[strtolower($caller)] ?? $caller;
            $agent_ext = '';
            if (preg_match('/user\/(\d{2,4})@/', $arg, $m)) $agent_ext = $m[1];
            elseif (preg_match('/^1\d{2}$/', $cc)) $agent_ext = $cc;
            elseif (preg_match('/^1\d{2}$/', $dest)) $agent_ext = $dest;
            elseif (preg_match('/^1\d{2}$/', $caller)) $agent_ext = $caller;
            elseif (preg_match('/(?:user\/)?(\d{2,4})@/', (string)($r['cc_agent_bridged'] ?? ''), $m)) $agent_ext = $m[1];
            $dir = strtolower(trim((string)($r['direction'] ?? '')));
            $dest_digits = preg_replace('/\D+/', '', $dest);
            $is_did = (bool)preg_match('/11113875[56]$/', $dest_digits)
                || (bool)preg_match('/11113875[56]$/', preg_replace('/\D+/', '', $cdest));
            if ($dir === '' || $dir === 'null') {
                if ($is_did || $dest === '8000') $dir = 'inbound';
                elseif (preg_match('/^1\d{2}$/', $caller) && !preg_match('/^1\d{2}$/', $dest)) $dir = 'outbound';
                elseif (preg_match('/^1\d{2}$/', $dest)) $dir = 'inbound';
                else $dir = 'inbound';
            }
            if (!preg_match('/^[\+\d\(\)\-\s#\*]{2,}$/', $dest)) {
                if (preg_match('/^[\+\d\(\)\-\s#\*]{2,}$/', $cdest)) $dest = $cdest;
                else continue;
            }
            if (strcasecmp($dest, 'unknown') === 0) {
                if (preg_match('/^[\+\d\(\)\-\s#\*]{2,}$/', $cdest)) $dest = $cdest;
                else continue;
            }
            $agent = '';
            if ($agent_ext !== '') {
                $agent = $agent_label[$agent_ext] ?? $agent_ext;
            }
            $rows[] = ['time'=>$r['call_time'],'caller'=>$caller !== '' ? $caller : '—',
                'destination'=>$dest,'agent'=>$agent !== '' ? $agent : '—',
                'direction'=>$dir,
                'duration'=>floor($b/60).':'.str_pad($b%60,2,'0',STR_PAD_LEFT),
                'status'=>$b>0?'Answered':'Missed','cause'=>$r['hangup_cause']??''];
        }"""

OLD_TH = """                    <th>Time</th><th>Caller</th><th>Destination</th>
                    <th>Direction</th><th>Duration</th><th>Status</th><th>Cause</th>"""
NEW_TH = """                    <th>Time</th><th>Caller</th><th>Destination</th><th>Agent</th>
                    <th>Direction</th><th>Duration</th><th>Status</th><th>Cause</th>"""

changed = False
if "r.agent||" in t and "last_arg, cc_agent" in t:
    print("supervisor.php already has Agent column")
else:
    if OLD_API not in t:
        sys.exit("call_history_all block not found (file already different)")
    t = t.replace(OLD_API, NEW_API, 1)
    t = t.replace(OLD_TH, NEW_TH, 1)
    t = t.replace('colspan="7"', 'colspan="8"')
    old_js = """            document.getElementById('chBody').innerHTML=rows.map(r=>`<tr>
                <td>${r.time}</td>
                <td>${r.caller}</td>
                <td>${r.destination}</td>
                <td><span class="badge-${r.direction==='outbound'?'out':'in'}">${r.direction}</span></td>"""
    new_js = """            document.getElementById('chBody').innerHTML=rows.map(r=>`<tr>
                <td>${r.time}</td>
                <td>${r.caller}</td>
                <td>${r.destination}</td>
                <td>${r.agent||'—'}</td>
                <td><span class="badge-${r.direction==='outbound'?'out':'in'}">${r.direction||'—'}</span></td>"""
    if old_js not in t:
        sys.exit("fetchCallHistory JS not found")
    t = t.replace(old_js, new_js, 1)
    P.write_text(t.replace("\r\n", "\n"), encoding="utf-8")
    print("patched", P)
    changed = True

# Tag inbound CDRs with direction + which agent was attempted (no FS recreate).
xml = subprocess.check_output(
    ["docker", "exec", "skykin-freeswitch", "cat", "/etc/freeswitch/dialplan/public/01_skykin_did.xml"],
    text=True,
)
orig = xml
if "call_direction=inbound" not in xml:
    xml = re.sub(
        r'(<action application="export" data="domain_name=[^"]+"/>)',
        r'\1\n      <action application="set" data="call_direction=inbound"/>\n      <action application="export" data="call_direction=inbound"/>',
        xml,
        count=1,
    )
if "cc_agent=101" not in xml:
    xml = re.sub(
        r'(<action application="bridge" data="[^"]*user/101@)',
        r'<action application="set" data="cc_agent=101"/>\n      \1',
        xml,
        count=1,
    )
if "cc_agent=102" not in xml:
    xml = re.sub(
        r'(<action application="bridge" data="[^"]*user/102@)',
        r'<action application="set" data="cc_agent=102"/>\n      \1',
        xml,
        count=1,
    )
if xml != orig:
    p = subprocess.Popen(
        ["docker", "exec", "-i", "skykin-freeswitch", "tee", "/etc/freeswitch/dialplan/public/01_skykin_did.xml"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
    )
    p.communicate(xml.encode())
    if p.returncode != 0:
        sys.exit("failed to write DID xml")
    subprocess.check_call(
        [
            "docker",
            "exec",
            "skykin-freeswitch",
            "fs_cli",
            "-H",
            "127.0.0.1",
            "-P",
            "8021",
            "-p",
            "SkykinEslChangeMe1",
            "-x",
            "reloadxml",
        ]
    )
    print("patched DID call_direction + cc_agent, reloadxml")
else:
    print("DID xml already has call_direction/cc_agent")

print("done")
if changed:
    print("hard-refresh supervisor: Ctrl+F5 on https://196.189.236.140:8188")
