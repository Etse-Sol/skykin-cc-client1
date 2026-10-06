-- B-leg hangup hook. 603 Decline must kill the Ethio caller.
-- Ring-timeout / 486 busy can still try the next agent (inbound.lua).
if not session then
  return
end

local api = freeswitch.API()

local function var(name)
  local v = session:getVariable(name)
  if v and v ~= "" and v ~= "_undef_" then return v end
  return ""
end

local ok, answered = pcall(function() return session:answered() end)
if ok and answered then
  return
end

local cause = string.upper(var("hangup_cause") .. " " .. var("proto_specific_hangup_cause") .. " " .. (argv[1] or ""))
if cause:find("NO_ANSWER", 1, true) or cause:find("ALLOTTED", 1, true)
    or cause:find("USER_NOT_REGISTERED", 1, true) then
  freeswitch.consoleLog("NOTICE", "skykin drop skip cause=" .. cause .. "\n")
  return
end

local member = var("originating_leg_uuid")
if member == "" then member = var("signal_bond") end
if member == "" then member = var("bridge_uuid") end
if member == "" then member = var("cc_member_session_uuid") end
if member == "" then member = var("cc_member_uuid") end
if member == "" then
  freeswitch.consoleLog("NOTICE", "skykin drop no-member cause=" .. cause .. "\n")
  return
end

freeswitch.consoleLog("NOTICE", "skykin drop caller=" .. member .. " cause=" .. cause .. "\n")
api:execute("uuid_kill", member .. " NORMAL_CLEARING")
