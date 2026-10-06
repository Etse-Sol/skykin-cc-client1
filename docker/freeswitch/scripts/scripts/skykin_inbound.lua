-- Ring the longest-idle Ready registered agent who is not already on a call.
-- Decline ends this customer call (does not roll to the next agent).
-- If every Ready agent is busy, park in callcenter so the caller waits.
if not session then
  return
end

local api = freeswitch.API()
local domain = session:getVariable("domain_name") or "client1.skykin.local"
local cid = session:getVariable("caller_id_number")
    or session:getVariable("ani")
    or session:getVariable("sip_from_user")
    or session:getVariable("effective_caller_id_number")
    or session:getVariable("sip_p_asserted_identity")
    or session:getVariable("sip_cid_num")
    or ""
if session:getVariable("skykin_blocked") == "true" or not session:ready() then
  session:execute("hangup", "CALL_REJECTED")
  return
end
local function bl_digits(s)
  s = (s or ""):gsub("%D", "")
  if s:sub(1, 3) == "251" and #s >= 12 then s = s:sub(4) end
  if #s == 10 and s:sub(1, 1) == "0" then s = s:sub(2) end
  return s
end
local function bl_file_hit(want, path)
  if domain == "" then return false end
  local f = io.open(path, "r")
  if not f then return false end
  for line in f:lines() do
    if line:sub(1, 1) ~= "#" and line ~= "" then
      local a, b = line:match("^([^|]+)|([^|]+)")
      if a == domain then
        local n = bl_digits(b or "")
        if n ~= "" then
          local k = math.min(#want, #n, 12)
          if k >= 7 and want:sub(-k) == n:sub(-k) then
            f:close()
            return true
          end
        end
      end
    end
  end
  f:close()
  return false
end
local function blacklisted()
  local want = bl_digits(cid)
  if #want < 7 or domain == "" then return false end
  local keys = { want, want:sub(-9), want:sub(-8), want:sub(-7), "251" .. want, "0" .. want }
  for _, key in ipairs(keys) do
    if #key >= 7 then
      local h = api:execute("hash", "select/skykin_bl/" .. domain .. "~" .. key) or ""
      h = h:gsub("%s+$", "")
      if h == "1" or h:match("^1%s") then
        return true
      end
    end
  end
  return bl_file_hit(want, "/etc/freeswitch/scripts/skykin_blacklist.txt")
      or bl_file_hit(want, "/var/lib/freeswitch/recordings/skykin_blacklist.txt")
end
if blacklisted() then
  freeswitch.consoleLog("NOTICE", "skykin blacklist drop cid=" .. cid .. "\n")
  session:setVariable("continue_on_fail", "false")
  session:setVariable("skykin_blocked", "true")
  session:execute("hangup", "CALL_REJECTED")
  error("skykin blocked")
end

-- After hours: ahununu only — play call-end-2 then drop.
-- ahununu: every day 08:00–19:00 Africa/Addis_Ababa.
-- Other domains (e.g. client1): no after-hours drop.
-- Override: skykin_biz_tz/open/close/days; skykin_biz_hours=off disables.
-- TEMP test bypass (no dialplan change):
--   docker exec skykin-freeswitch touch /etc/freeswitch/scripts/skykin_biz_hours_off
-- Restore hours:
--   docker exec skykin-freeswitch rm -f /etc/freeswitch/scripts/skykin_biz_hours_off
local function outside_business_hours()
  local bypass = io.open("/etc/freeswitch/scripts/skykin_biz_hours_off", "r")
  if bypass then
    bypass:close()
    freeswitch.consoleLog("NOTICE", "skykin after-hours BYPASSED (skykin_biz_hours_off present)\n")
    return false
  end
  local disabled = (session:getVariable("skykin_biz_hours") or ""):lower()
  if disabled == "off" or disabled == "0" or disabled == "false" then
    return false
  end
  -- Only ahununu uses the closed-hours behavior.
  if domain ~= "ahununu" then
    return false
  end
  local tz = session:getVariable("skykin_biz_tz") or "Africa/Addis_Ababa"
  local open_hm = tonumber(session:getVariable("skykin_biz_open") or "0800") or 800
  local close_hm = tonumber(session:getVariable("skykin_biz_close") or "1900") or 1900
  local days_raw = session:getVariable("skykin_biz_days") or "1,2,3,4,5,6,7"
  local allowed = {}
  for d in tostring(days_raw):gmatch("%d+") do
    allowed[tonumber(d)] = true
  end
  local raw = api:execute("strftime_tz", tz .. " %u %H%M") or ""
  raw = raw:gsub("%s+$", "")
  local dow_s, hm_s = raw:match("(%d+)%s+(%d+)")
  local dow = tonumber(dow_s or "")
  local hm = tonumber(hm_s or "")
  if not dow or not hm then
    freeswitch.consoleLog("WARNING", "skykin hours parse fail raw=[" .. raw .. "]\n")
    return false
  end
  if not allowed[dow] then
    return true
  end
  if hm < open_hm or hm >= close_hm then
    return true
  end
  return false
end

if outside_business_hours() then
  freeswitch.consoleLog("NOTICE", "skykin after-hours drop domain=" .. domain
    .. " cid=" .. cid .. "\n")
  session:setVariable("continue_on_fail", "false")
  session:setVariable("skykin_after_hours", "true")

  -- Save caller for morning callback (Callbacks tab). Best-effort; never block hangup.
  -- Host-network FS cannot resolve compose hostname "web" — use 127.0.0.1:WEB_PORT
  -- (same pattern as CDR_URL). Always append shared-volume queue as backup.
  do
    local did = session:getVariable("destination_number")
      or session:getVariable("sip_to_user")
      or session:getVariable("Caller-Destination-Number")
      or ""
    local uuid = session:getVariable("uuid") or ""
    local key = os.getenv("SKYKIN_AH_CB_KEY") or "skykin-ah-cb-2026"
    local phone = cid:gsub("%s+", "")
    local called_at = ""
    do
      local raw_t = api:execute("strftime_tz", "Africa/Addis_Ababa %Y-%m-%d %H:%M:%S") or ""
      called_at = raw_t:gsub("%s+$", "")
    end
    local function urlenc(s)
      return (tostring(s or ""):gsub("([^%w%-%.%_%~ ])", function(c)
        return string.format("%%%02X", string.byte(c))
      end))
    end
    local function queue_file()
      local f = io.open("/var/lib/freeswitch/recordings/skykin_after_hours_queue.txt", "a")
      if not f then return false end
      f:write((called_at ~= "" and called_at or os.date("!%Y-%m-%dT%H:%M:%SZ"))
        .. "|" .. domain .. "|" .. phone .. "|" .. did .. "|" .. uuid .. "\n")
      f:close()
      freeswitch.consoleLog("NOTICE", "skykin after-hours callback queued file\n")
      return true
    end
    local function curl_ok(res)
      res = tostring(res or "")
      if res == "" or res:find("%-ERR") or res:find("curl:") then return false end
      return res:find('"ok"%s*:%s*true') ~= nil
    end
    if phone ~= "" and #bl_digits(phone) >= 7 then
      -- Shared volume with skykin-web — cron drain picks this up if HTTP fails.
      queue_file()
      local q = "key=" .. urlenc(key)
        .. "&phone=" .. urlenc(phone)
        .. "&domain=" .. urlenc(domain)
        .. "&did=" .. urlenc(did)
        .. "&uuid=" .. urlenc(uuid)
        .. "&called_at=" .. urlenc(called_at)
      local bases = {}
      local env_url = os.getenv("SKYKIN_AH_CB_URL") or ""
      if env_url ~= "" then bases[#bases + 1] = env_url end
      -- Prefer host-published HTTP (FS is network_mode:host on ecs-cc).
      bases[#bases + 1] = "http://127.0.0.1:8190/app/agent_dashboard/skykin_after_hours_cb.php"
      bases[#bases + 1] = "http://127.0.0.1:8080/app/agent_dashboard/skykin_after_hours_cb.php"
      bases[#bases + 1] = "http://127.0.0.1:8090/app/agent_dashboard/skykin_after_hours_cb.php"
      bases[#bases + 1] = "http://web/app/agent_dashboard/skykin_after_hours_cb.php"
      local saved = false
      for _, base in ipairs(bases) do
        local url = base .. "?" .. q
        local ok_curl, res = pcall(function()
          return api:execute("curl", url)
        end)
        freeswitch.consoleLog("NOTICE", "skykin after-hours callback try "
          .. base .. " res=" .. tostring(res):sub(1, 160) .. "\n")
        if ok_curl and curl_ok(res) then
          saved = true
          break
        end
      end
      if not saved then
        -- Host curl binary (mod_curl may be unloaded / return -ERR without Lua error).
        local url = "http://127.0.0.1:8190/app/agent_dashboard/skykin_after_hours_cb.php?" .. q
        pcall(function()
          os.execute("curl -fsS --max-time 3 '" .. url:gsub("'", "'\\''") .. "' >/dev/null 2>&1")
        end)
      end
    else
      freeswitch.consoleLog("WARNING", "skykin after-hours callback skip bad cid=["
        .. tostring(cid) .. "]\n")
    end
  end

  local root = "/var/lib/freeswitch/recordings/" .. domain
  local closed_wav = session:getVariable("skykin_biz_closed_wav")
      or os.getenv("FS_CLOSED_WAV")
      or ""
  local closed_candidates = {
    closed_wav,
    root .. "/call-end-2.wav",
    root .. "/ahununu-call-end.wav",
    root .. "/voice-call-end-2.wav",
    root .. "/Call_End_2.wav",
    root .. "/call_end_2.wav",
    root .. "/closed.wav",
  }
  local function play_closed(path)
    if path == nil or path == "" then return false end
    local f = io.open(path, "r")
    if not f then return false end
    f:close()
    local ok, answered = pcall(function() return session:answered() end)
    if not (ok and answered) then
      session:execute("pre_answer")
    end
    freeswitch.consoleLog("NOTICE", "skykin after-hours play " .. path .. "\n")
    session:streamFile(path)
    return true
  end
  for _, path in ipairs(closed_candidates) do
    if play_closed(path) then
      break
    end
  end
  session:execute("hangup", "NORMAL_CLEARING")
  return
end

-- Conversation-only recording: clear ANY record-on-answer hooks before we
-- answer for caller audio. Recording starts only when the agent B-leg answers.
session:setVariable("execute_on_answer", "")
session:setVariable("api_on_answer", "")
session:setVariable("record_session", "")
session:setVariable("media_bug_answer_req", "")
session:setVariable("skykin_record_after_agent", "true")

-- Desired flow:
--   Call enters queue → agent rings IMMEDIATELY
--   Caller hears opening-long once, then music loops
--   Agent may answer during opening OR during music
-- Opening is NOT a blocking playback before hunt — it is ringback on A-leg.
local root_rec = "/var/lib/freeswitch/recordings/" .. domain
local function first_existing(list)
  for _, path in ipairs(list) do
    if path and path ~= "" then
      local f = io.open(path, "r")
      if f then f:close(); return path end
    end
  end
  return nil
end
local opening_path = first_existing({
  session:getVariable("skykin_welcome_wav") or os.getenv("FS_WELCOME_WAV") or "",
  root_rec .. "/opening-long.wav",
  root_rec .. "/opening.wav",
  root_rec .. "/welcome.wav",
})
local music_path = first_existing({
  session:getVariable("skykin_music_wav") or os.getenv("FS_MUSIC_WAV") or "",
  root_rec .. "/music.wav",
})
local waiting_path = first_existing({
  session:getVariable("skykin_waiting_wav") or os.getenv("FS_WAITING_WAV") or "",
  root_rec .. "/waiting-2.wav",
})

-- Answer so Ethio hears our audio instead of PSTN ringtone.
session:setVariable("execute_on_answer", "")
do
  local ok, answered = pcall(function() return session:answered() end)
  if not (ok and answered) then
    freeswitch.consoleLog("NOTICE", "skykin inbound answer (caller audio + agent hunt)\n")
    session:execute("answer")
  end
end
-- Clear carrier ringtone before opening (media latch).
session:execute("playback", "silence_stream://500")

-- Opening ONCE with no ringback underneath (ringback is armed only after this).
if opening_path and session:ready() then
  freeswitch.consoleLog("NOTICE", "skykin opening once=" .. opening_path .. "\n")
  session:streamFile(opening_path)
end

-- ONLY after opening: music loops while agents ring.
local ringback = nil
if music_path then
  ringback = "{loops=-1}" .. music_path
end
if ringback then
  session:setVariable("ringback", ringback)
  session:execute("export", "ringback=" .. ringback)
  session:setVariable("transfer_ringback", ringback)
  freeswitch.consoleLog("NOTICE", "skykin ringback music-only (after opening)=" .. ringback .. "\n")
end
if music_path then
  session:setVariable("hold_music", music_path)
  session:setVariable("cc_moh_override", music_path)
  session:execute("export", "cc_moh_override=" .. music_path)
  local ev = session:getVariable("cc_export_vars") or ""
  if not ev:find("cc_moh_override", 1, true) then
    if ev == "" then
      session:setVariable("cc_export_vars", "cc_moh_override")
    else
      session:setVariable("cc_export_vars", ev .. ",cc_moh_override")
    end
  end
  freeswitch.consoleLog("NOTICE", "skykin music loop=" .. music_path .. "\n")
end
if waiting_path then
  freeswitch.consoleLog("NOTICE", "skykin waiting prompt=" .. waiting_path .. "\n")
end

local queue = "8000@" .. domain
-- Agent WebRTC must use the PUBLIC RTP IP. Inbound A-leg often has
-- rtp_advertise_ip=LAN (10.0.0.77) for the carrier leg — reusing that
-- broke agent ringing (caller heard ringback, softphone never showed).
local function public_rtp_ip()
  local env = os.getenv("EXTERNAL_RTP_IP") or ""
  if env ~= "" then return env end
  local sess = session:getVariable("rtp_advertise_ip") or session:getVariable("rtp_ext_ip") or ""
  if sess ~= ""
      and not sess:match("^10%.")
      and not sess:match("^192%.168%.")
      and not sess:match("^172%.(1[6-9]|2%d|3[0-1])%.") then
    return sess
  end
  return "196.189.236.126"
end
local rtp_ip = public_rtp_ip()
freeswitch.consoleLog("NOTICE", "skykin inbound agent rtp_ip=" .. rtp_ip .. "\n")

-- Do NOT hang up the Ethio caller when an agent leg fails.
-- hangup_after_bridge=true was killing A-leg on NORMAL_TEMPORARY_FAILURE
-- (instant agent softphone fail) → silence/ringtone then drop.
session:setVariable("hangup_after_bridge", "false")
session:setVariable("continue_on_fail", "true")
session:setVariable("ignore_early_media", "true")
session:setVariable("bridge_early_media", "false")
session:setVariable("instant_ringback", "true")

-- Keep recording hooks empty until agent answers.
session:setVariable("execute_on_answer", "")
session:setVariable("record_stereo", "true")
session:setVariable("RECORD_STEREO", "true")
session:setVariable("recording_follow_transfer", "true")

local function ensure_record_vars()
  local domain_name = session:getVariable("domain_name") or domain
  local path = session:getVariable("record_path") or ""
  local name = session:getVariable("record_name") or ""
  if path == "" or path:find("%{", 1, true) or path:find("${", 1, true) then
    local y = (api:execute("strftime", "%Y") or "2026"):gsub("%s+", "")
    local mon = (api:execute("strftime", "%b") or "Jan"):gsub("%s+", "")
    local d = (api:execute("strftime", "%d") or "01"):gsub("%s+", "")
    path = "/var/lib/freeswitch/recordings/" .. domain_name
      .. "/archive/" .. y .. "/" .. mon .. "/" .. d
    session:setVariable("record_path", path)
  end
  if name == "" then
    name = (session:getVariable("uuid") or "call") .. ".wav"
    session:setVariable("record_name", name)
  end
  api:execute("system", "mkdir -p '" .. path .. "'")
  return path .. "/" .. name
end

local function agent_bridge_string(dest, rec_file, a_uuid)
  -- Start A-leg recording only when the agent B-leg answers (not during IVR).
  local domain_name = session:getVariable("domain_name") or domain
  local on_answer = "lua /etc/freeswitch/scripts/skykin_record_on_agent.lua "
    .. a_uuid .. " " .. rec_file .. " " .. dest .. " " .. domain_name
  local contact = api:execute("sofia_contact", "*/" .. dest .. "@" .. domain) or ""
  -- ALWAYS WebRTC for ahununu dashboard agents.
  -- They register via skykin-ws-sip as UDP@10.0.0.77, but Chrome still needs
  -- DTLS fingerprint. The UDP-vs-WebRTC split caused Answer failed / silence.
  -- Reverted to the known-working path: media_webrtc=true on every agent leg.
  -- Prefer rtp_secure_media=true so Chrome gets DTLS-SRTP (silence if we allow
  -- plain RTP fallback via optional). 503s under load are handled by tech-fail
  -- retry/cooldown below — do not trade those for silent "answered" calls.
  local leg = "[leg_timeout=30,media_webrtc=true,rtp_secure_media=true,rtp_advertise_ip="
    .. rtp_ip .. ",include_external_ip=true]"
  freeswitch.consoleLog("NOTICE", "skykin bridge webrtc dest=" .. dest
    .. " contact=" .. tostring(contact):sub(1, 140) .. "\n")
  return "{hangup_after_bridge=true,ignore_early_media=true,bridge_early_media=false,originate_timeout=45,"
    .. "api_on_answer='" .. on_answer .. "'}"
    .. leg .. "user/" .. dest .. "@" .. domain
end

local function cols(line)
  local c = {}
  for x in (line .. "|"):gmatch("(.-)|") do c[#c + 1] = x end
  return c
end

local function registered(ext)
  local r = api:execute("sofia_contact", "*/" .. ext .. "@" .. domain) or ""
  if r:find("error", 1, true) or r:find("user_not_registered", 1, true) then
    return false
  end
  return r:find("sip:", 1, true) ~= nil
end

local function on_a_call(ext)
  local chans = api:execute("show", "channels") or ""
  return chans:find("user/" .. ext .. "@" .. domain, 1, true) ~= nil
      or chans:find("/" .. ext .. "@" .. domain, 1, true) ~= nil
end

-- True longest-idle: last ACTIVITY = max(last_bridge_end, last_offered, ready_time, our hash).
-- Lua rings bypass mod_callcenter, so last_offered often stays stuck equal for all agents;
-- we always stamp ready_time + hash on each offer/answer so ranking stays real.
local function agent_idle_stamp(ext, agent_key, epoch)
  epoch = tonumber(epoch) or os.time()
  if ext and ext ~= "" then
    api:execute("hash", "insert/skykin_agent_idle/" .. ext .. "/" .. tostring(epoch))
  end
  if agent_key and agent_key ~= "" then
    api:execute("callcenter_config",
      "agent set ready_time " .. agent_key .. " " .. tostring(epoch))
  end
end

local function agent_idle_hash(ext)
  if not ext or ext == "" then return 0 end
  return tonumber(api:execute("hash", "select/skykin_agent_idle/" .. ext) or "") or 0
end

local function ready_agents(skip)
  -- Longest-idle: smallest last-activity epoch = idle longest → rings first.
  local out = api:execute("callcenter_config", "queue list agents " .. queue) or ""
  local best = {} -- ext -> { ext, idle, name, uuid, salt }
  for line in out:gmatch("[^\r\n]+") do
    if line:find("|", 1, true) and line:sub(1, 5) ~= "name|" then
      local c = cols(line)
      local ext = (c[5] or ""):match("user/([^@]+)")
      local status, state = c[6] or "", c[7] or ""
      if ext and not skip[ext]
          and status == "Available" and (state == "Waiting" or state == "Idle")
          and registered(ext) and not on_a_call(ext) then
        local bridge_end = tonumber(c[14]) or 0
        local offered = tonumber(c[15]) or 0
        local ready = tonumber(c[20]) or 0
        local hashed = agent_idle_hash(ext)
        -- Real last activity = most recent of all signals (not offered-only).
        local idle = bridge_end
        if offered > idle then idle = offered end
        if ready > idle then idle = ready end
        if hashed > idle then idle = hashed end
        local prev = best[ext]
        if not prev or idle < prev.idle then
          best[ext] = {
            ext = ext,
            idle = idle,
            name = c[1] or "",
            uuid = c[1] or "",
            salt = math.random(1, 1000000),
            bridge_end = bridge_end,
            offered = offered,
            ready = ready,
            hashed = hashed,
          }
        end
      end
    end
  end
  local rows = {}
  for _, row in pairs(best) do
    rows[#rows + 1] = row
  end
  table.sort(rows, function(a, b)
    if a.idle == b.idle then
      -- Fair tie-break (do NOT prefer lowest ext / Agent 1).
      return a.salt < b.salt
    end
    return a.idle < b.idle -- smaller epoch = idle longer
  end)
  if #rows > 0 then
    local order = {}
    for i = 1, #rows do
      local r = rows[i]
      order[i] = string.format(
        "%s(idle=%s b=%s o=%s r=%s h=%s)",
        r.ext, tostring(r.idle), tostring(r.bridge_end),
        tostring(r.offered), tostring(r.ready), tostring(r.hashed)
      )
    end
    freeswitch.consoleLog("NOTICE", "skykin longest-idle order " .. table.concat(order, ",") .. "\n")
  end
  return rows
end

-- Softphone / WebRTC bridge died under load (503 / TEMPORARY_FAILURE).
-- Distinct from NO_ANSWER (agent didn't click) — these need retry + music wait.
local function is_softphone_tech_fail(cause, disp, sip)
  cause = string.upper(tostring(cause or ""))
  disp = string.upper(tostring(disp or ""))
  sip = tostring(sip or "")
  if cause:find("TEMPORARY_FAILURE", 1, true)
      or disp:find("TEMPORARY_FAILURE", 1, true) then
    return true
  end
  if sip == "503" or sip == "480" or sip == "408" then
    return true
  end
  if cause == "INCOMPATIBLE_DESTINATION"
      or cause == "DESTINATION_OUT_OF_ORDER"
      or cause == "RECOVERY_ON_TIMER_EXPIRE" then
    return true
  end
  return false
end

local function note_softphone_fail(dest, cause, sip)
  -- WARNING line is scraped by scripts/skykin_bridge_fail_alert.sh
  freeswitch.consoleLog("WARNING", "skykin softphone_fail dest="
    .. tostring(dest) .. " cause=" .. tostring(cause)
    .. " sip=" .. tostring(sip) .. " domain=" .. tostring(domain) .. "\n")
end

local rec_file = ensure_record_vars()
local a_uuid = session:getVariable("uuid") or ""

-- Mark A-leg so agent/supervisor dashboards can list Lua-wait callers
-- (callcenter members stay empty by design — local music wait, not mod_callcenter).
-- Use channel var + hash: presence_data alone often missing from "show channels as json".
local function set_queue_wait_visible(on)
  local uuid = session:getVariable("uuid") or a_uuid or ""
  local caller = session:getVariable("caller_id_number") or cid or ""
  if on then
    session:setVariable("presence_data", "skykin_queue_wait")
    session:setVariable("skykin_queue_wait", "true")
    if uuid ~= "" then
      api:execute("hash", "insert/skykin_qwait/" .. uuid .. "/"
        .. caller .. "|" .. domain .. "|" .. tostring(os.time()))
    end
    freeswitch.consoleLog("NOTICE", "skykin queue wait VISIBLE uuid=" .. uuid
      .. " cid=" .. caller .. "\n")
  else
    session:setVariable("presence_data", "")
    session:setVariable("skykin_queue_wait", "")
    if uuid ~= "" then
      api:execute("hash", "delete/skykin_qwait/" .. uuid)
    end
  end
end

local skip = {}
local retry_once = {} -- dest -> already did one quick re-ring after tech fail
local busy_announced = false
local tech_fail_rounds = 0

while session:ready() do
  local agents = ready_agents(skip)
  local dest = agents[1] and agents[1].ext
  if not dest then
    -- No Ready agent (or all skipped after softphone fails): wait with music,
    -- then clear skip/retry so agents get another chance under load.
    set_queue_wait_visible(true)
    freeswitch.consoleLog("NOTICE", "skykin inbound queue wait (local music loop) "
      .. queue .. " tech_fail_rounds=" .. tostring(tech_fail_rounds) .. "\n")
    if not busy_announced then
      busy_announced = true
      skip = {}
      retry_once = {}
      tech_fail_rounds = 0
      if waiting_path and session:ready() then
        freeswitch.consoleLog("NOTICE", "skykin busy play waiting " .. waiting_path .. "\n")
        session:streamFile(waiting_path)
      end
    else
      -- Subsequent waits under load: still refresh skip so dead contacts can recover.
      skip = {}
      retry_once = {}
    end
    if not session:ready() then
      return
    end
    if music_path then
      freeswitch.consoleLog("NOTICE", "skykin busy music loop tick=" .. music_path .. "\n")
      session:streamFile(music_path)
    else
      session:sleep(5000)
    end
  else
    busy_announced = false
    set_queue_wait_visible(false)
    local last_agent_key = agents[1].uuid or agents[1].name or dest
    local bridge = agent_bridge_string(dest, rec_file, a_uuid)
    freeswitch.consoleLog("NOTICE", "skykin inbound try " .. dest .. "@" .. domain
      .. " rec=" .. rec_file
      .. " retry=" .. tostring(retry_once[dest] == true) .. "\n")
    -- Stamp offer time so this agent is no longer "longest idle".
    agent_idle_stamp(dest, last_agent_key, os.time())
    session:execute("bridge", bridge)
    local cause = string.upper(session:getVariable("last_bridge_hangup_cause")
        or session:getVariable("originate_disposition") or "")
    local disp = string.upper(session:getVariable("originate_disposition") or "")
    local sip = session:getVariable("sip_invite_failure_status") or ""
    freeswitch.consoleLog("NOTICE", "skykin inbound cause=" .. cause
      .. " disp=" .. disp .. " sip=" .. sip .. " dest=" .. dest
      .. " ready=" .. tostring(session:ready()) .. "\n")

    if disp == "SUCCESS" then
      -- Agent connected: mark activity now so they rotate fairly after the call.
      agent_idle_stamp(dest, last_agent_key, os.time())
      return
    end
    if not session:ready() then
      freeswitch.consoleLog("NOTICE", "skykin inbound A-leg gone after try "
        .. dest .. " cause=" .. cause .. "\n")
      return
    end

    if is_softphone_tech_fail(cause, disp, sip) then
      tech_fail_rounds = tech_fail_rounds + 1
      note_softphone_fail(dest, cause, sip)
      freeswitch.consoleLog("WARNING", "skykin inbound softphone tech fail dest="
        .. dest .. " cause=" .. cause .. " sip=" .. sip
        .. " round=" .. tostring(tech_fail_rounds) .. "\n")
      if not retry_once[dest] then
        -- Load blip: same Ready agent often works on immediate second try.
        retry_once[dest] = true
        freeswitch.consoleLog("NOTICE", "skykin inbound retry once " .. dest .. "\n")
        session:sleep(800)
      else
        skip[dest] = true
        -- Cooldown: stop re-offering a dead softphone for ~90s (SKYKIN_SOFTPHONE_HARDEN_v1).
        agent_idle_stamp(dest, last_agent_key, os.time() + 90)
        freeswitch.consoleLog("NOTICE", "skykin inbound tech-fail cooldown 90s "
          .. dest .. " key=" .. tostring(last_agent_key) .. "\n")
        freeswitch.consoleLog("NOTICE", "skykin inbound roll next after tech fail "
          .. dest .. " cause=" .. cause .. "\n")
        -- Brief music so we don't originate-storm every Ready agent under load.
        if music_path and tech_fail_rounds >= 2 and session:ready() then
          set_queue_wait_visible(true)
          session:streamFile(music_path)
        else
          session:sleep(300)
        end
      end
    else
      -- Real no-answer / busy / cancel: next agent.
      skip[dest] = true
      freeswitch.consoleLog("NOTICE", "skykin inbound roll next after " .. dest
        .. " cause=" .. cause .. "\n")
      session:sleep(200)
    end
  end
end
