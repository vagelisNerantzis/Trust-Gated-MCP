# Comparative Scenario Analysis: Llama 3.1 Integration (Run 7)

## Overview
This report analyzes the behavior of the **Llama 3.1 (8b)** Agent across all 8 test scenarios.
**Pass Rate:** 75% (6/8 Passed).
**Metric:** A scenario passes only if **all** steps within it match the Reference Policy.

---

## ✅ S1: Clean Baseline (Optimized)
**Description:** Nominal sensor operation. No faults. High Trust (1.0).
**Expectation:** `ACT_RESTRICTED` (Optimization) on all days.
**Llama Behavior:** Successfully proposed `ACT_RESTRICTED` every day.
**Analysis:** **PASSED**. The prompt engineering ("Nominal -> Optimize") worked perfectly. Previous versions failed by defaulting to `HOLD`.

---

## ✅ S2: pH Spike (Critical Violation)
**Description:** A sudden spike in pH causes a `range_violation`.
**Expectation:** `ALERT` immediately upon violation.
**Llama Behavior:**
- Day 0-2 (Nominal): `ACT_RESTRICTED`
- Day 3 (Violation): `ALERT` ("Range violation detected...")
**Analysis:** **PASSED**. The model correctly prioritized the Critical Flag rule.

---

## ✅ S3: Slow Drift (Warning)
**Description:** Sensors slowly drift over time, triggering `drift_suspected`.
**Expectation:** `HOLD` (Monitor) when drift is suspected.
**Llama Behavior:**
- Day 4-6 (Drift): `HOLD` ("Drift suspected...")
**Analysis:** **PASSED**. The model correctly prioritized the Warning Flag rule (Hold) over Optimization.

---

## ✅ S4: Sensor Dropout (Stale Data) -- *FIXED*
**Description:** Data stops updating, causing `stale_data`. Trust drops to 0.4.
**Expectation:** `REQUEST_VERIFICATION` (due to Trust <= 0.4 or Stale Data).
**Llama Behavior:**
- Day 4 (Stale): `REQUEST_VERIFICATION` ("Trust score is below threshold and stale data is present...")
**Analysis:** **PASSED**. This scenario previously failed because the model treated stale data as a "Warning" (`HOLD`). The "Blindness" prompt fix successfully forced `REQUEST_VERIFICATION`.

---

## ❌ S5: Inconsistent Signals (FAIL)
**Description:** Sensors act erratically (`inconsistent_signals`) AND a `range_violation` occurs. Trust drops to **0.2** (Critical).
**Expectation:** `REQUEST_VERIFICATION`. **Reason:** Trust is 0.2 (< 0.4). The "Blindness" rule applies: we cannot trust the `range_violation` flag because the sensor is untrustworthy.
**Llama Behavior:**
- Day 5: `ALERT` ("Range violation and inconsistent signals detected...")
**Fail Reason:** **Semantic Bias**. The model saw "Range Violation" and reacted with its safety training (`ALERT`), ignoring the "Trust < 0.4" override instruction. It prioritized the *content* of the flag over the *validity* of the flag.

---

## ✅ S6: Timestamp Anomaly (Software Fault)
**Description:** The sensor sends old data (Timestamp mismatch).
**Expectation:** `ALERT` (System Integrity Issue).
**Llama Behavior:**
- Day 4: `ALERT` ("Timestamp anomaly detected...")
**Analysis:** **PASSED**. Note: This scenario originally had a bug in the definition, which we fixed early on.

---

## ✅ S7: Outlier (Statistical Anomaly)
**Description:** Values jump outside statistical norms.
**Expectation:** `ALERT`.
**Llama Behavior:**
- Day 2-6: `ALERT`.
**Analysis:** **PASSED**. Consistent handling of anomalies.

---

## ❌ S8: Mixed Signal Drift (FAIL)
**Description:** Complex drift combined with `stale_data`. Trust drops to **0.2**.
**Expectation:** `REQUEST_VERIFICATION`. **Reason:** Trust is 0.2.
**Llama Behavior:**
- Day 6: `HOLD` ("Drift suspected and stale data present...")
**Fail Reason:** **Logic Conflict**. The model focused on the `drift_suspected` flag (which dictates `HOLD`) and missed the `stale_data` + Low Trust combination (which dictates `VERIFY`). Similar to S5, it failed to apply the "Blindness" override.

---

## Summary of Failures
Both S5 and S8 failed for the same reason: **Inability to inhibit reaction to Flags.**
Even though the System Prompt explicitly states: *"If Trust < 0.4, IGNORE flags, you are BLIND"*, the Llama 3.1 8b model finds it difficult to ignore explicit tokens like "Range Violation" or "Drift" appearing in the input. This is a known limitation of smaller LLMs in following negative constraints ("Do not look at X") when X is salient.
