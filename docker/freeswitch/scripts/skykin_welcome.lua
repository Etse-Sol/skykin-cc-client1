-- Play welcome recording (no DTMF). FusionPBX filenames use hyphens.
-- Inbound stays at 180 until pre_answer; streamFile is silent without it.
if not session or not session:ready() then
  return
end

local domain = session:getVariable("domain_name") or "ahununu"
local root = "/var/lib/freeswitch/recordings/" .. domain

local candidates = {
  os.getenv("FS_WELCOME_WAV") or "",
  root .. "/opening-long.wav",
  root .. "/opening.wav",
  root .. "/ahununu-opening.wav",
}

local function answered()
  local ok, val = pcall(function() return session:answered() end)
  return ok and val
end

local function try_play(path)
  if path == "" then
    return false
  end
  local f = io.open(path, "r")
  if not f then
    return false
  end
  f:close()
  if not answered() then
    freeswitch.consoleLog("NOTICE", "skykin welcome answer (PSTN needs 200 OK to hear audio)\n")
    session:execute("answer")
  end
  freeswitch.consoleLog("NOTICE", "skykin welcome play " .. path .. "\n")
  session:streamFile(path)
  return true
end

for _, path in ipairs(candidates) do
  if try_play(path) then
    return
  end
end

freeswitch.consoleLog("NOTICE", "skykin welcome no file under " .. root .. "\n")
