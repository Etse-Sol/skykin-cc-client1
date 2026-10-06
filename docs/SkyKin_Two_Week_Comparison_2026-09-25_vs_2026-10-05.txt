# SkyKin / Ahununu — Two-Week Progress Comparison

**Week A (baseline):** Report as of **25 Sep 2026** (~7 days prior)  
**Week B (current):** Report as of **5 Oct 2026** (~7 days prior)  
**Sources:** [SkyKin_Inbound_Complaint_Report_2026-09-25](SkyKin_Inbound_Complaint_Report_2026-09-25.md) · [SkyKin_Weekly_Report_2026-10-05](SkyKin_Weekly_Report_2026-10-05.md)

### Scope notes (fair comparison)
| | Week A (25 Sep) | Week B (5 Oct) |
|--|-----------------|----------------|
| Inbound DIDs | `11619803*` | `11619803[5-9]` + `116901*` |
| Hours used in abandon split | Before 08 / 08–18 / after 18 | Before 08:30 / 08:30–19:00 / after 19 |
| KPI base | Reportable talk legs | Talk legs (billsec > 0) |

Percent answer/abandon are comparable; absolute DID volume in Week B is slightly broader (legacy 690 lines included).

---

## 1. Progress snapshot

| Metric | Week A (~25 Sep) | Week B (~5 Oct) | Change |
|--------|-----------------:|----------------:|--------|
| Answer rate (agent connected / talk) | **41.9%** | **52.0%** | **+10.1 pts** |
| Abandon rate (no agent / talk) | **58.1%** | **48.0%** | **−10.1 pts** |
| Answered (count) | 315 | 378 | **+63** |
| Abandoned (count) | 436 | 349 | **−87** |
| Talk / reportable volume | 751 | 727* | similar |
| Platform health | Healthy | Healthy | Stable |

\*Week B talk = answered + abandoned = 378 + 349 = 727 (plus 78 zero-bill legs outside that %).

**Verdict:** Clear **service progress** — more callers reach agents, fewer abandon after hearing the system. Platform stayed healthy both weeks.

---

## 2. Side-by-side KPI

| Metric | Week A | Week B |
|--------|-------:|-------:|
| Inbound (scoped) | 751 reportable | 805 legs (727 with talk) |
| Answered — agent connected | 315 (41.9%) | 378 (52.0%) |
| Abandoned — no agent | 436 (58.1%) | 349 (48.0%) |
| Missed / zero bill | 0 (reported) | 78 |

---

## 3. When abandons happen (coverage)

| Window | Week A | Week B |
|--------|--------|--------|
| Early / before open | Before 08:00: **226 (~52%)** | Before 08:30: **41 (~12%)** |
| Open / daytime | 08–18: **209 (~48%)** | 08:30–19:00: **273 (~78%)** |
| Late / after close | After 18:00: **1 (~0%)** | After 19:00: **35 (~10%)** |

**What improved**
- Far fewer **pre-shift** abandons in Week B share (early coverage better, or traffic pattern changed).

**What still needs work**
- Week B abandons are **mostly inside open hours** (staffing / lunch peak — esp. hour 13).
- Week B late abandons (**35**) are higher than Week A’s after-18 count partly because **after-hours is still bypassed** (nights still queue instead of closed + callback).

---

## 4. Ring-then-abandon by agent

| Ext | Week A | Week B | Change |
|----:|-------:|-------:|--------|
| 201 | 78 | 63 | −15 |
| 202 | 29 | 42 | +13 |
| 203 | 48 | 9 | −39 |
| 204 | 5 | 17 | +12 |
| 205 | 10 | — | — |

**Read:** Less ring-no-connect on 201/203 overall; 202 more active (more offered). Oct 3 still showed single-agent overload risk.

---

## 5. Best / worst days (Week B only)

| Day | Answer % of talk | Note |
|-----|-----------------:|------|
| **5 Oct** | **~78%** | Best — multi-agent Ready (dashboard later ~85 ans / 19 abd) |
| 3 Oct | **~24%** | Worst — queue wait, understaffed (logs confirmed) |
| 4 Oct | ~21% | Low volume / weak coverage |

Week A did not publish a daily table; Week B shows progress is **real but uneven** — good days are excellent; thin staffing collapses the rate.

---

## 6. Platform & after-hours

| Item | Week A | Week B | Progress |
|------|--------|--------|----------|
| FreeSWITCH / DB / web | Up ~10d healthy | Up ~2 weeks healthy | Stable |
| Disk `/` | 74% | 76% | Watch |
| Disk `/var` | 79% | 61% | Better |
| After-hours closed + callback | Recommended | Still **OFF** (bypass since 18 Sep) | **Not done** |
| Outbound recording | — | On-answer fix 5 Oct | Improved hygiene |

---

## 7. What got better / what didn’t

### Better
1. **+10 pts answer rate** (42% → 52%).  
2. **−87 abandoned** calls week-over-week.  
3. **+63 more** agent-connected calls.  
4. Platform remained stable; `/var` disk pressure eased.  
5. Strong days (e.g. 5 Oct) prove the stack can run at high connect rates with proper coverage.

### Not yet / risks
1. **After-hours still bypassed** — nights not closed; new AH callbacks not live.  
2. **Open-hours abandons** still the main pile (273 in Week B).  
3. **Midday (13:00)** and thin-staff days (3–4 Oct) still hurt the week average.  
4. Softphone edge cases (silent live / ICE) remain occasional, not the main KPI driver.

---

## 8. Management one-pager

| | |
|--|--|
| **Progress** | Answer rate up ~**10 percentage points**; abandons down. |
| **System** | Healthy both weeks — not a trunk outage story. |
| **Remaining gap** | Staffing inside **08:30–19:00** (especially lunch) + turn **after-hours ON**. |
| **Next actions** | ≥2 Ready agents at peak; Ready by 08:30; remove `skykin_biz_hours_off`; keep weekly answer/abandon tracking. |

---

*Comparison built from the 25 Sep and 5 Oct SkyKin reports on ecs-cc CDR data.*
