# SkyKin / Ahununu Call Center — Inbound Performance Report
**Period:** Last 7 days (as of 25 Sep 2026 ~08:40 UTC / 11:40 EAT)  
**Source:** FreeSWITCH CDR (`v_xml_cdr`) on ecs-cc + FreeSWITCH logs (sample cases)  
**Scope:** Inbound DIDs matching `11619803*`

---

## 1. Executive summary

| Finding | Result |
|--------|--------|
| Platform health | **Healthy** (FreeSWITCH, DB, web up ~10 days; WS-SIP active) |
| Inbound answer-to-agent rate | **~42%** |
| Abandoned (system answered, no agent connected) | **~58%** |
| Main driver of client complaints | Abandoned / not connected to a live agent |
| PBX systematically blocking agent Answer? | **No evidence** for ring-then-abandon set (~97% `NORMAL_CLEARING`) |
| Ownership | Mostly **coverage + agent pickup**; platform up; rare softphone/media issues |

---

## 2. Platform status (ops check)

| Component | Status |
|-----------|--------|
| skykin-freeswitch | Up 10 days (healthy) |
| skykin-db | Up 10 days (healthy) |
| skykin-web | Up 10 days |
| skykin-ws-sip | active |
| Host load | ~0.20 (low) |
| Disk `/` | 74% used |
| Disk `/var` | 79% used (monitor recordings) |

**Verdict:** No platform outage at time of check.

---

## 3. Inbound KPI (7 days, reportable legs)

| Metric | Count | % |
|--------|------:|--:|
| Reportable inbound calls | 751 | 100% |
| **Answered — agent connected** | **315** | **41.9%** |
| **Abandoned — IVR/system answered, agent NOT connected** | **436** | **58.1%** |
| Missed (no IVR talk) | 0 | 0% |

> “Answered by agent” = real bridge (`cc_agent_bridged` / `bridge_uuid` / wait+talk proof).  
> “Abandoned” = customer heard system (billsec > 0) but **never connected to an agent**.

---

## 4. Abandoned timing (EAT) — coverage vs open hours

| Window | Abandoned | Share of abandons |
|--------|----------:|------------------:|
| Before 08:00 | 226 | ~52% |
| 08:00–18:00 | 209 | ~48% |
| After 18:00 | 1 | ~0% |
| **Total abandoned** | **436** | 100% |

**Interpretation**
- ~Half of abandons are **before shift / early morning** → agents not logged in yet.
- ~Half are **during daytime** → Available/registered + answer discipline still required.

Hourly abandon peaks (EAT): **08:00 (55)**, 07:00 (44), 05:00 (42), 02:00 (40), 10:00 (40).

---

## 5. Abandoned: was an agent rung?

| Category | Count | Share |
|----------|------:|------:|
| Abandoned total (billsec > 0, not connected) | ~432 | 100% |
| Agent was offered/rung (`last_arg` user/2xx) then abandoned | **170** | **~39%** |
| No agent offered in CDR (remainder) | **~262** | **~61%** |

### 5a. Ring-then-abandon by extension

| Agent ext | Abandoned after ring |
|----------:|---------------------:|
| 201 | 78 |
| 203 | 48 |
| 202 | 29 |
| 205 | 10 |
| 204 | 5 |

### 5b. Proof: system block vs no pickup (rung → abandoned)

| Hangup cause | Count | Meaning |
|--------------|------:|---------|
| **NORMAL_CLEARING** | **162** | Caller/wait cleared; agent did not connect — **not PBX block-answer** |
| MEDIA_TIMEOUT | 2 | Possible media issue |
| NORMAL_UNSPECIFIED | 2 | Unclear |
| INTERWORKING | 1 | Network interworking |
| ALLOTTED_TIMEOUT / NORMAL_TEMPORARY_FAILURE / INCOMPATIBLE_DESTINATION | **0** | **None** in this set |

**Conclusion:** For calls where an agent was rung and the call still abandoned, there is **no CDR evidence that the PBX prevented Answer**. Almost all cleared as normal without agent connect (= no pickup / caller gave up).

---

## 6. Softphone / media issues (separate, smaller)

| Cause (7 days, all directions sample) | Count |
|---------------------------------------|------:|
| NORMAL_TEMPORARY_FAILURE | 46 |
| INCOMPATIBLE_DESTINATION | 4 |

**Known verified cases (logs):**
- Inbound silent after answer (e.g. `251938666888` ~14:46 EAT): agent bridged + DTLS OK; customer audio on recording; agent softphone path silent → **WebRTC/network**, not “no answer.”
- Outbound `INCOMPATIBLE_DESTINATION` (e.g. 203 → 911502296): log `no suitable candidates found` → **agent ICE/WebRTC**, number format OK.

These explain some “answered but not really talking” reports, but they are **not** the bulk of the ~58% abandon rate.

---

## 7. Mapping client complaint language

| Client statement | Finding |
|------------------|---------|
| Calls not properly responded to | **Confirmed** — ~58% abandoned without agent connect |
| Call personal phones due to CC issues | **Consistent** with low connect rate |
| Appear answered in system but not connected to agent | **Confirmed** — PBX answers IVR/music first; if no agent connects → Abandoned |
| Permanent PBX outage | **Not supported** — platform healthy |

---

## 8. Recommendations

### Client / operations
1. Publish **official open hours**; after-hours announcement + callback.  
2. All agents **Registered + Available by shift start (e.g. 08:00)**.  
3. Enforce **answer when softphone rings** (focus ext **201**, then **203**).  
4. Report every “silent after answer” with time + caller + agent ext.

### SkyKin / platform
1. Keep monitoring platform health and disk (`/var` recordings).  
2. Continue softphone/WebRTC hardening for rare media/ICE cases.  
3. Weekly report: answered % / abandoned % / ring-no-answer by extension.

---

## 9. Bottom line

- **Server:** OK.  
- **Service:** ~**42%** of inbound reach an agent; ~**58%** abandon after system answer.  
- **Complaints:** Valid on **unanswered / not connected to agent**.  
- **Not mainly:** PBX preventing agents from answering.  
- **Mainly:** **before-login coverage** + **daytime ring-no-answer / availability**.

---

*Report generated from ecs-cc CDR queries and FreeSWITCH log samples. Regenerate anytime with `scripts/skykin_inbound_complaint_report.sh` on the server.*
