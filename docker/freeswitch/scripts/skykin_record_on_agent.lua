-- Start stereo recording on the caller (A-leg) when the agent (B-leg) answers.
-- Also stamp cc_agent_bridged so CDR Answered is reliable (lua bridge does not
-- set that field by itself — last_arg alone is set on failed rings too).
-- Args: <a-uuid> <full-wav-path> [agent-ext] [domain]
local api = freeswitch.API()
local a_uuid = argv[1] or ""
local file = argv[2] or ""
local ext = argv[3] or ""
local domain = argv[4] or ""
if a_uuid == "" or file == "" then
  freeswitch.consoleLog("WARNING", "skykin_record_on_agent missing uuid/file\n")
  return
end
local dir = file:match("(.+)/[^/]+$")
if dir and dir ~= "" then
  api:execute("system", "mkdir -p '" .. dir .. "'")
end
if ext ~= "" and domain ~= "" then
  api:execute("uuid_setvar", a_uuid .. " cc_agent_bridged /" .. ext .. "@" .. domain)
  api:execute("uuid_setvar", a_uuid .. " cc_agent /" .. ext .. "@" .. domain)
end
api:execute("uuid_setvar", a_uuid .. " skykin_agent_answered true")
api:execute("uuid_setvar", a_uuid .. " RECORD_STEREO true")
api:execute("uuid_setvar", a_uuid .. " recording_follow_transfer true")
local res = api:execute("uuid_record", a_uuid .. " start " .. file) or ""
freeswitch.consoleLog("NOTICE", "skykin_record_on_agent start " .. a_uuid
  .. " agent=" .. ext .. " -> " .. file .. " res=" .. tostring(res) .. "\n")
