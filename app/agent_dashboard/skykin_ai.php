<?php
/**
 * SkyKin AI helpers — internal STT + scoring for ACW / Evaluation.
 *
 * Default: your internal model service (not OpenAI cloud).
 *
 * Modes (SKYKIN_AI_MODE):
 *   skykin         One-shot: POST recording → {transcript, scores, notes}
 *   openai_compat  OpenAI-compatible /audio/transcriptions + /chat/completions
 *                  (works with local Whisper + vLLM/Ollama/OpenAI-compatible gateways)
 *
 * Config (merge order: defaults ← /etc/skykin/ai.env ← skykin_ai.local.php ← getenv):
 *   SKYKIN_AI=on|off
 *   SKYKIN_AI_MODE=skykin|openai_compat
 *   SKYKIN_AI_BASE_URL=http://127.0.0.1:8100
 *   SKYKIN_AI_API_KEY=   (optional for internal LAN)
 *   SKYKIN_AI_EVAL_PATH=/v1/evaluate
 *   SKYKIN_AI_TRANSCRIBE_PATH=/v1/audio/transcriptions
 *   SKYKIN_AI_CHAT_PATH=/v1/chat/completions
 *   SKYKIN_AI_MODEL=...
 *   SKYKIN_AI_WHISPER_MODEL=...
 */
declare(strict_types=1);

if (!function_exists('skykin_ai_config')) {

function skykin_ai_config(): array {
    static $cfg = null;
    if ($cfg !== null) {
        return $cfg;
    }
    $cfg = [
        'enabled' => true,
        'mode' => 'skykin', // internal one-shot evaluate by default
        'api_key' => '',
        'base_url' => 'http://127.0.0.1:8100',
        'eval_path' => '/v1/evaluate',
        'transcribe_path' => '/v1/audio/transcriptions',
        'chat_path' => '/v1/chat/completions',
        'chat_model' => 'skykin-qa',
        'whisper_model' => 'whisper',
        'timeout' => 180,
        'require_api_key' => false,
    ];

    $applyKv = static function (array &$cfg, string $k, string $v): void {
        switch ($k) {
            case 'OPENAI_API_KEY':
            case 'SKYKIN_AI_API_KEY':
                $cfg['api_key'] = $v;
                break;
            case 'SKYKIN_AI_BASE_URL':
            case 'OPENAI_BASE_URL':
                $cfg['base_url'] = rtrim($v, '/');
                break;
            case 'SKYKIN_AI_MODE':
                $cfg['mode'] = strtolower($v);
                break;
            case 'SKYKIN_AI_MODEL':
            case 'SKYKIN_AI_CHAT_MODEL':
                $cfg['chat_model'] = $v;
                break;
            case 'SKYKIN_AI_WHISPER_MODEL':
                $cfg['whisper_model'] = $v;
                break;
            case 'SKYKIN_AI_EVAL_PATH':
                $cfg['eval_path'] = $v[0] === '/' ? $v : ('/' . $v);
                break;
            case 'SKYKIN_AI_TRANSCRIBE_PATH':
                $cfg['transcribe_path'] = $v[0] === '/' ? $v : ('/' . $v);
                break;
            case 'SKYKIN_AI_CHAT_PATH':
                $cfg['chat_path'] = $v[0] === '/' ? $v : ('/' . $v);
                break;
            case 'SKYKIN_AI_TIMEOUT':
                $cfg['timeout'] = max(30, (int)$v);
                break;
            case 'SKYKIN_AI_REQUIRE_KEY':
                $cfg['require_api_key'] = in_array(strtolower($v), ['1', 'true', 'yes', 'on'], true);
                break;
            case 'SKYKIN_AI':
                if (in_array(strtolower($v), ['off', '0', 'false'], true)) {
                    $cfg['enabled'] = false;
                } elseif (in_array(strtolower($v), ['on', '1', 'true'], true)) {
                    $cfg['enabled'] = true;
                }
                break;
        }
    };

    $envFile = '/etc/skykin/ai.env';
    if (is_readable($envFile)) {
        foreach (file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) ?: [] as $line) {
            $line = trim($line);
            if ($line === '' || $line[0] === '#' || strpos($line, '=') === false) {
                continue;
            }
            [$k, $v] = explode('=', $line, 2);
            $applyKv($cfg, trim($k), trim($v, " \t\"'"));
        }
    }

    $local = __DIR__ . '/skykin_ai.local.php';
    if (is_readable($local)) {
        $arr = include $local;
        if (is_array($arr)) {
            $cfg = array_merge($cfg, $arr);
        }
    }

    foreach ([
        'OPENAI_API_KEY', 'SKYKIN_AI_API_KEY', 'SKYKIN_AI_BASE_URL', 'OPENAI_BASE_URL',
        'SKYKIN_AI_MODE', 'SKYKIN_AI_MODEL', 'SKYKIN_AI_CHAT_MODEL', 'SKYKIN_AI_WHISPER_MODEL',
        'SKYKIN_AI_EVAL_PATH', 'SKYKIN_AI_TRANSCRIBE_PATH', 'SKYKIN_AI_CHAT_PATH',
        'SKYKIN_AI_TIMEOUT', 'SKYKIN_AI_REQUIRE_KEY', 'SKYKIN_AI',
    ] as $ek) {
        $v = getenv($ek);
        if (is_string($v) && $v !== '') {
            $applyKv($cfg, $ek, $v);
        }
    }

    // Legacy: if someone only set openai.com URL, treat as openai_compat
    if (stripos((string)$cfg['base_url'], 'api.openai.com') !== false && ($cfg['mode'] ?? '') === 'skykin') {
        $cfg['mode'] = 'openai_compat';
        $cfg['require_api_key'] = true;
        if (($cfg['transcribe_path'] ?? '') === '/v1/audio/transcriptions') {
            /* ok */
        }
        if (empty($cfg['chat_model']) || $cfg['chat_model'] === 'skykin-qa') {
            $cfg['chat_model'] = 'gpt-4o-mini';
        }
        if (empty($cfg['whisper_model']) || $cfg['whisper_model'] === 'whisper') {
            $cfg['whisper_model'] = 'whisper-1';
        }
    }

    return $cfg;
}

function skykin_ai_ready(): bool {
    $c = skykin_ai_config();
    if (empty($c['enabled']) || empty($c['base_url'])) {
        return false;
    }
    if (!empty($c['require_api_key']) && empty($c['api_key'])) {
        return false;
    }
    return true;
}

/** @return array{ok:bool,error?:string,body?:string,http?:int} */
function skykin_ai_http(string $method, string $url, array $headers, $body, int $timeout = 120): array {
    if (!function_exists('curl_init')) {
        return ['ok' => false, 'error' => 'curl extension missing'];
    }
    $ch = curl_init($url);
    $hdrs = [];
    foreach ($headers as $k => $v) {
        $hdrs[] = is_int($k) ? $v : ($k . ': ' . $v);
    }
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => $timeout,
        CURLOPT_HTTPHEADER => $hdrs,
        CURLOPT_POSTFIELDS => $body,
    ]);
    $raw = curl_exec($ch);
    $err = curl_error($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($raw === false) {
        return ['ok' => false, 'error' => $err ?: 'curl failed', 'http' => $code];
    }
    if ($code < 200 || $code >= 300) {
        return ['ok' => false, 'error' => 'HTTP ' . $code . ': ' . substr((string)$raw, 0, 400), 'http' => $code, 'body' => (string)$raw];
    }
    return ['ok' => true, 'body' => (string)$raw, 'http' => $code];
}

function skykin_ai_auth_headers(): array {
    $c = skykin_ai_config();
    if (empty($c['api_key'])) {
        return [];
    }
    return ['Authorization' => 'Bearer ' . $c['api_key']];
}

function skykin_ai_curl_file(string $absolutePath): CURLFile {
    $mime = 'application/octet-stream';
    $ext = strtolower(pathinfo($absolutePath, PATHINFO_EXTENSION));
    $map = [
        'webm' => 'audio/webm', 'wav' => 'audio/wav', 'mp3' => 'audio/mpeg',
        'ogg' => 'audio/ogg', 'm4a' => 'audio/mp4', 'mp4' => 'audio/mp4',
    ];
    if (isset($map[$ext])) {
        $mime = $map[$ext];
    }
    return new CURLFile($absolutePath, $mime, basename($absolutePath));
}

/**
 * Resolve recording on disk from softphone filename and/or CDR fields.
 */
function skykin_ai_resolve_recording(string $domain, string $filename = '', string $recordPath = '', string $recordName = ''): string {
    if (!function_exists('skykin_recording_path')) {
        require_once __DIR__ . '/skykin_config.php';
    }
    $file = $filename !== '' ? $filename : $recordName;
    $file = basename($file);
    if ($file === '') {
        return '';
    }
    $dir = $recordPath !== '' ? rtrim($recordPath, '/') : '';
    return skykin_recording_path($file, $domain, $dir);
}

function skykin_ai_normalize_scores(array $d): array {
    $scores = [];
    foreach (['greeting', 'knowledge', 'resolution', 'tone', 'procedure', 'closing'] as $k) {
        $v = (int)($d['score_' . $k] ?? $d[$k] ?? 3);
        $scores[$k] = max(1, min(5, $v));
    }
    return $scores;
}

/**
 * Internal SkyKin evaluate API:
 *   POST {base}{eval_path}  multipart: file, meta JSON fields
 * Expected JSON (flexible):
 *   { "ok": true, "transcript": "...", "scores": {...} or score_greeting..., "notes": "..." }
 *   or OpenAI-ish { "text": "...", ...scores... }
 */
function skykin_ai_eval_skykin(string $absolutePath, array $meta = []): array {
    $c = skykin_ai_config();
    $url = rtrim($c['base_url'], '/') . $c['eval_path'];
    $post = [
        'file' => skykin_ai_curl_file($absolutePath),
        'meta' => json_encode($meta, JSON_UNESCAPED_UNICODE),
        'domain' => (string)($meta['domain'] ?? ''),
        'caller' => (string)($meta['caller'] ?? ''),
        'agent_ext' => (string)($meta['agent_ext'] ?? ''),
        'direction' => (string)($meta['direction'] ?? ''),
        'duration' => (string)(int)($meta['duration'] ?? 0),
        'task' => 'evaluation',
    ];
    $res = skykin_ai_http('POST', $url, skykin_ai_auth_headers(), $post, (int)$c['timeout']);
    if (empty($res['ok'])) {
        return ['ok' => false, 'error' => $res['error'] ?? 'internal evaluate failed'];
    }
    $j = json_decode((string)$res['body'], true);
    if (!is_array($j)) {
        return ['ok' => false, 'error' => 'Internal model returned non-JSON'];
    }
    if (isset($j['ok']) && $j['ok'] === false) {
        return ['ok' => false, 'error' => (string)($j['error'] ?? 'evaluate rejected')];
    }
    $transcript = trim((string)($j['transcript'] ?? $j['text'] ?? ''));
    $scoresSrc = is_array($j['scores'] ?? null) ? $j['scores'] : $j;
    $scores = skykin_ai_normalize_scores($scoresSrc);
    $notes = trim((string)($j['notes'] ?? $j['evaluator_notes'] ?? ''));
    return [
        'ok' => true,
        'scores' => $scores,
        'notes' => $notes,
        'transcript' => $transcript,
        'provider' => 'skykin',
    ];
}

/**
 * Transcribe via OpenAI-compatible endpoint on internal (or cloud) base URL.
 * @return array{ok:bool,text?:string,error?:string}
 */
function skykin_ai_transcribe(string $absolutePath): array {
    if (!skykin_ai_ready()) {
        return ['ok' => false, 'error' => 'AI not configured (set SKYKIN_AI_BASE_URL in /etc/skykin/ai.env)'];
    }
    if ($absolutePath === '' || !is_readable($absolutePath)) {
        return ['ok' => false, 'error' => 'Recording file not found yet'];
    }
    $size = filesize($absolutePath);
    if ($size === false || $size < 500) {
        return ['ok' => false, 'error' => 'Recording too short or empty'];
    }
    if ($size > 24 * 1024 * 1024) {
        return ['ok' => false, 'error' => 'Recording too large for transcription'];
    }
    $c = skykin_ai_config();
    $url = rtrim($c['base_url'], '/') . $c['transcribe_path'];
    $post = [
        'file' => skykin_ai_curl_file($absolutePath),
        'model' => $c['whisper_model'],
        'response_format' => 'json',
    ];
    $res = skykin_ai_http('POST', $url, skykin_ai_auth_headers(), $post, (int)$c['timeout']);
    if (empty($res['ok'])) {
        return ['ok' => false, 'error' => $res['error'] ?? 'transcribe failed'];
    }
    $j = json_decode((string)$res['body'], true);
    $text = trim((string)($j['text'] ?? $j['transcript'] ?? ''));
    if ($text === '') {
        return ['ok' => false, 'error' => 'Empty transcript'];
    }
    return ['ok' => true, 'text' => $text];
}

/**
 * Chat completion → JSON object (parsed). OpenAI-compatible.
 * @return array{ok:bool,data?:array,error?:string,raw?:string}
 */
function skykin_ai_chat_json(string $system, string $user): array {
    if (!skykin_ai_ready()) {
        return ['ok' => false, 'error' => 'AI not configured'];
    }
    $c = skykin_ai_config();
    $payload = json_encode([
        'model' => $c['chat_model'],
        'temperature' => 0.2,
        'response_format' => ['type' => 'json_object'],
        'messages' => [
            ['role' => 'system', 'content' => $system],
            ['role' => 'user', 'content' => $user],
        ],
    ], JSON_UNESCAPED_UNICODE);
    $headers = array_merge(skykin_ai_auth_headers(), ['Content-Type' => 'application/json']);
    $url = rtrim($c['base_url'], '/') . $c['chat_path'];
    $res = skykin_ai_http('POST', $url, $headers, $payload, (int)$c['timeout']);
    if (empty($res['ok'])) {
        return ['ok' => false, 'error' => $res['error'] ?? 'chat failed'];
    }
    $j = json_decode((string)$res['body'], true);
    $content = (string)($j['choices'][0]['message']['content'] ?? $j['content'] ?? '');
    if ($content === '' && isset($j['scores'])) {
        return ['ok' => true, 'data' => $j, 'raw' => (string)$res['body']];
    }
    $data = json_decode($content, true);
    if (!is_array($data)) {
        return ['ok' => false, 'error' => 'Model did not return JSON', 'raw' => $content];
    }
    return ['ok' => true, 'data' => $data, 'raw' => $content];
}

/** @return array{ok:bool,disposition?:string,call_reason?:string,notes?:string,transcript?:string,error?:string} */
function skykin_ai_acw_draft(string $transcript, string $callerId = '', string $callType = '', int $duration = 0): array {
    $system = <<<'SYS'
You are a call-center wrap-up assistant for SkyKin / Ahununu (Ethiopia).
Given a call transcript, return JSON only with keys:
- disposition: one of Resolved, Follow-Up, Escalated, Completed Normally, Invalid
- call_reason: short label (max 40 chars), e.g. Billing, Order status, Complaint
- notes: 2-4 factual sentences for the agent ACW notes. No invented order IDs or amounts.
If transcript is empty or unclear, use disposition Completed Normally and say so in notes.
SYS;
    $user = "Caller: {$callerId}\nCall type: {$callType}\nDuration seconds: {$duration}\n\nTranscript:\n{$transcript}";
    $r = skykin_ai_chat_json($system, $user);
    if (empty($r['ok'])) {
        return ['ok' => false, 'error' => $r['error'] ?? 'draft failed'];
    }
    $d = $r['data'];
    $allowed = ['Resolved', 'Follow-Up', 'Escalated', 'Completed Normally', 'Invalid'];
    $disp = (string)($d['disposition'] ?? 'Completed Normally');
    if (!in_array($disp, $allowed, true)) {
        $disp = 'Completed Normally';
    }
    return [
        'ok' => true,
        'disposition' => $disp,
        'call_reason' => mb_substr(trim((string)($d['call_reason'] ?? 'General')), 0, 80),
        'notes' => trim((string)($d['notes'] ?? '')),
        'transcript' => $transcript,
    ];
}

/**
 * Score call 1-5 on evaluation criteria from transcript (LLM path).
 * @return array{ok:bool,scores?:array,notes?:string,transcript?:string,error?:string}
 */
function skykin_ai_eval_draft(string $transcript, array $meta = []): array {
    $system = <<<'SYS'
You are a QA coach scoring a call-center recording for SkyKin.
Score each criterion from 1 to 5 (integers). Return JSON:
{
  "score_greeting": 1-5,
  "score_knowledge": 1-5,
  "score_resolution": 1-5,
  "score_tone": 1-5,
  "score_procedure": 1-5,
  "score_closing": 1-5,
  "notes": "short evaluator notes with evidence from the call"
}
Criteria:
1 greeting = introduction / identify company / ask how to help
2 knowledge = accurate product/service info
3 resolution = solved or clear next step
4 tone = professional, calm, respectful
5 procedure = followed process (verify, confirm, no unsafe promises)
6 closing = thank you / confirm / goodbye
Be fair; lack of audio clarity should not auto-zero everything — use mid scores and explain in notes.
SYS;
    $user = 'Meta: ' . json_encode($meta, JSON_UNESCAPED_UNICODE) . "\n\nTranscript:\n{$transcript}";
    $r = skykin_ai_chat_json($system, $user);
    if (empty($r['ok'])) {
        return ['ok' => false, 'error' => $r['error'] ?? 'eval failed'];
    }
    $d = $r['data'];
    return [
        'ok' => true,
        'scores' => skykin_ai_normalize_scores($d),
        'notes' => trim((string)($d['notes'] ?? '')),
        'transcript' => $transcript,
        'provider' => 'openai_compat',
    ];
}

/**
 * Full pipeline: file → transcript → ACW draft.
 */
function skykin_ai_acw_from_file(string $path, string $callerId = '', string $callType = '', int $duration = 0): array {
    $t = skykin_ai_transcribe($path);
    if (empty($t['ok'])) {
        return $t;
    }
    return skykin_ai_acw_draft((string)$t['text'], $callerId, $callType, $duration);
}

/**
 * Full pipeline for Evaluation: internal one-shot, or transcribe + score.
 * @return array{ok:bool,scores?:array,notes?:string,transcript?:string,error?:string,provider?:string}
 */
function skykin_ai_eval_from_file(string $path, array $meta = []): array {
    if (!skykin_ai_ready()) {
        return ['ok' => false, 'error' => 'AI not configured. Point SKYKIN_AI_BASE_URL at your internal model in /etc/skykin/ai.env'];
    }
    if ($path === '' || !is_readable($path)) {
        return ['ok' => false, 'error' => 'Recording file not found yet'];
    }
    $c = skykin_ai_config();
    $mode = strtolower((string)($c['mode'] ?? 'skykin'));

    if ($mode === 'skykin' || $mode === 'internal') {
        $one = skykin_ai_eval_skykin($path, $meta);
        // If the dedicated evaluate route is missing, fall back to compat STT+chat.
        if (empty($one['ok']) && isset($one['error']) && preg_match('/HTTP 404|HTTP 405/', (string)$one['error'])) {
            $mode = 'openai_compat';
        } else {
            return $one;
        }
    }

    $t = skykin_ai_transcribe($path);
    if (empty($t['ok'])) {
        return $t;
    }
    return skykin_ai_eval_draft((string)$t['text'], $meta);
}

} // function_exists guard
