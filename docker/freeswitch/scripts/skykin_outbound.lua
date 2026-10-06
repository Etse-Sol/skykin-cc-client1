-- Outbound to Ethio: do not answer the agent before the mobile answers.
-- When the mobile Declines/Busy, always hang up the agent leg.
-- Record the conversation once the B-leg answers (same archive layout as inbound).
if not session then
  return
end

local gw = argv[1] or "SIP8035"
local dest = argv[2] or ""
local cid = argv[3] or dest
local lan = argv[4] or "10.0.0.77"

if dest == "" then
  freeswitch.consoleLog("ERR", "skykin_outbound: empty dest\n")
  session:hangup("NO_ROUTE_DESTINATION")
  return
end

freeswitch.consoleLog("NOTICE", "skykin_outbound gw=" .. gw .. " dest=" .. dest .. " cid=" .. cid .. "\n")

local api = freeswitch.API()
local a_uuid = session:getVariable("uuid") or ""
local domain_name = session:getVariable("domain_name")
  or session:getVariable("domain")
  or "ahununu"
local y = (api:execute("strftime", "%Y") or "2026"):gsub("%s+", "")
local mon = (api:execute("strftime", "%b") or "Jan"):gsub("%s+", "")
local d = (api:execute("strftime", "%d") or "01"):gsub("%s+", "")
local rec_path = "/var/lib/freeswitch/recordings/" .. domain_name
  .. "/archive/" .. y .. "/" .. mon .. "/" .. d
local rec_name = a_uuid .. ".wav"
local rec_file = rec_path .. "/" .. rec_name
api:execute("system", "mkdir -p '" .. rec_path .. "'")
session:setVariable("domain_name", domain_name)
session:execute("export", "domain_name=" .. domain_name)
session:setVariable("call_direction", "outbound")
session:execute("export", "call_direction=outbound")
session:setVariable("record_path", rec_path)
session:setVariable("record_name", rec_name)
session:setVariable("record_stereo", "true")
session:setVariable("RECORD_STEREO", "true")
session:setVariable("recording_follow_transfer", "true")
session:execute("export", "record_path=" .. rec_path)
session:execute("export", "record_name=" .. rec_name)

session:setVariable("hangup_after_bridge", "true")
session:setVariable("continue_on_fail", "false")
session:setVariable("call_timeout", "60")
-- Instant local ringback to the WebRTC agent (tone_stream = no wav file delay).
-- Keep ignore_early_media=true so Ethio 183 early-media does not break WebRTC.
local ringback = "tone_stream://%(2000,4000,440,480);loops=-1"
session:setVariable("ringback", ringback)
session:setVariable("transfer_ringback", ringback)
session:execute("export", "ringback=" .. ringback)
session:execute("export", "transfer_ringback=" .. ringback)
session:setVariable("instant_ringback", "true")
session:setVariable("ignore_early_media", "true")
session:execute("export", "instant_ringback=true")
session:execute("export", "ignore_early_media=true")

-- Start recording when the mobile answers (B-leg), not while ringing.
local on_answer = "uuid_record " .. a_uuid .. " start " .. rec_file
-- Do not string.format() ringback — tone_stream uses %( which breaks format.
local bridge =
  "{ignore_early_media=true,instant_ringback=true,ringback=" .. ringback
  .. ",transfer_ringback=" .. ringback
  .. ",originate_timeout=60,absolute_codec_string=^^:PCMA:PCMU,rtcp=-1,"
  .. "rtp_secure_media=false,media_webrtc=false,rtp_advertise_ip=" .. lan
  .. ",include_external_ip=false,"
  .. "origination_caller_id_number=" .. cid
  .. ",origination_caller_id_name=" .. cid
  .. ",api_on_answer='" .. on_answer .. "'}sofia/gateway/" .. gw .. "/" .. dest

freeswitch.consoleLog("NOTICE", "skykin_outbound ringback=tone_stream instant=true rec_on_answer="
  .. rec_file .. "\n")
session:execute("bridge", bridge)

-- Propagate the real B-leg outcome to the agent softphone (not always CALL_REJECTED).
-- That lets the dashboard show Busy / Switched off / No answer instead of generic "Call ended".
if session:ready() then
  local cause = string.upper(session:getVariable("last_bridge_hangup_cause")
      or session:getVariable("originate_disposition") or "")
  local hang = "NORMAL_TEMPORARY_FAILURE"
  if cause == "USER_BUSY" then
    hang = "USER_BUSY"
  elseif cause == "CALL_REJECTED" then
    hang = "CALL_REJECTED"
  -- Ethio hangup to agent/CDR (UI maps NO_USER_RESPONSE → No answer).
  -- Keep cause codes distinct; dashboard labels them.
  elseif cause == "NORMAL_TEMPORARY_FAILURE" or cause == "DESTINATION_OUT_OF_ORDER"
      or cause == "ALLOTTED_TIMEOUT" or cause == "NO_RESPONSE" then
    hang = "NORMAL_TEMPORARY_FAILURE"
  elseif cause == "NO_USER_RESPONSE" or cause == "NO_ANSWER"
      or cause == "SUBSCRIBER_ABSENT" or cause == "USER_NOT_REGISTERED" then
    hang = "NO_USER_RESPONSE"
  elseif cause == "UNALLOCATED_NUMBER" or cause == "NO_ROUTE_DESTINATION"
      or cause == "INVALID_NUMBER_FORMAT" then
    hang = "UNALLOCATED_NUMBER"
  elseif cause == "ORIGINATOR_CANCEL" then
    hang = "ORIGINATOR_CANCEL"
  elseif cause == "NORMAL_CLEARING" then
    hang = "NORMAL_CLEARING"
  elseif cause ~= "" then
    hang = cause
  end
  freeswitch.consoleLog("NOTICE", "skykin_outbound hangup agent cause=" .. hang
    .. " bleg=" .. cause .. "\n")
  session:hangup(hang)
end
