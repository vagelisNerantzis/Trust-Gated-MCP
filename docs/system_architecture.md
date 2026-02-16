# System Architecture Analysis: TrustGatedMCP_V2

## 1. High-Level Concept: The Trust Gate Pattern
This project implements a **Trust-Gated Model Context Protocol (MCP)** for Industrial Control Systems (ICS).
The core philosophy is that **AI Agents (LLMs) should not have direct control** over critical physical infrastructure. Instead, their actions must pass through a "Trust Gate" which evaluates the safety of the action based on:
1.  **Sensor Reliability**: Is the data fresh and consistent?
2.  **System State**: Are we in a nominal or anomaly state?
3.  **Agent Trustworthiness**: Has the agent been behaving correctly recently?

If the **Trust Score** is high, the Agent acts with **Full Autonomy**.
If the Trust Score is low, the Agent is blocked or restricted to **Suggestion Mode** (Human-in-the-loop).

## 2. Core Data Flow

```mermaid
graph TD
    S[Sensors (Bioreactor)] -->|Data| TE[Trust Engine]
    TE -->|Trust Score & Flags| MCP[Spirulina MCP Server]
    MCP -->|Context (State + Trust)| AG[LLM Agent (Llama 3.1)]
    AG -->|Proposed Action| MCP
    MCP -->|Gate Check| TG{Trust Gate}
    TG -->|Pass| ACT[Execute Action]
    TG -->|Fail| BLK[Block / Downgrade]
```

## 3. Control Algorithms (The "Brains" of the Gate)

The reliability of the Trust Gate depends on the `TrustEngine` (in `trust_engine/core.py`), which uses scientific algorithms to quantify safety.

### A. Anomaly Detection Algorithms
1.  **Z-Score Analysis (Outlier Detection)**
    *   **Goal**: Detect sudden spikes (e.g., pH sensor failure).
    *   **Logic**: $Z = \frac{x - \mu}{\sigma}$. If $|Z| > 3.0$ (3-Sigma Rule), flag `range_violation`.
    *   **Why**: Standard statistical method for Gaussian distributions.

2.  **CUSUM Control Chart (Drift Detection)**
    *   **Goal**: Detect slow, subtle drifts that Z-Score misses.
    *   **Logic**: Accumulates deviations over time.
        *   $S^+ = \max(0, S^+ + z - k)$
        *   $S^- = \max(0, S^- - z - k)$
        *   If $S > h$, flag `drift_suspected`.
    *   **Parameters**: $k=0.5$ (Slack), $h=5.0$ (Threshold).

3.  **Physics-Based Residuals (Consistency Check)**
    *   **Goal**: Detect if sensors contradict physical laws.
    *   **Logic**: If Temp < 28°C (Cold), Biology dictates Growth < 0.8.
        *   If `temp < 28.0` AND `growth > 0.8` -> `inconsistent_signals`.
    *   **Why**: Hard physics constraints are the ultimate truth check.

### B. Trust Score Calculation
The Trust Score (0.0 - 1.0) is calculated deterministically by applying penalties:

| Flag | Penalty | Reason |
| :--- | :--- | :--- |
| **Timestamp Anomaly** | `-1.0` (Instant Block) | Old data is dangerous. |
| **Stale Data** | `-0.6` | System is blind. |
| **Range Violation** | `-0.5` | Critical safety limit. |
| **Inconsistent Signal**| `-0.3` | Sensor disagreement. |
| **Drift Suspected** | `-0.2` | Early warning. |

### C. Gate Enforcement Logic
The `SpirulinaMCP` enforces permissions based on the calculated Score:

*   **FULL_AUTONOMY (Score ≥ 0.8)**: All Actions Allowed.
*   **SAFE_ONLY (Score ≥ 0.6)**: `ACT_RESTRICTED` (Optimization) is **Blocked**. Only Safety actions allowed.
*   **SUGGEST_ONLY (Score ≥ 0.4)**: All Active Control (`ACT_SAFE`, `ACT_RESTRICTED`) is **Blocked**. Only `ALERT` or `VERIFY`.
*   **BLOCK (Score < 0.4)**: **Everything Blocked** except `REQUEST_VERIFICATION`. System is legally blind.

## 4. Detailed File Breakdown

### A. Core Infrastructure (`experiments/core/`)
-   **`types.py`**: Defines the fundamental data structures using Pydantic.

### B. The Trust Engine (`experiments/trust_engine/`)
-   **`core.py`**: Implementation of the algorithms described in Section 3.

### C. The Server (`experiments/mcp_server.py`)
-   **`SpirulinaMCP` Class**: Implements the Gate Enforcement Logic described in Section 3C.

### D. The Agent (`experiments/llm_agent/`)
-   **`agent.py`**: The Llama 3.1 integration.

### E. The Scenarios (`experiments/scenarios/`)
-   **`generator.py`**: The simulation ground truth.

### F. The Policy (`experiments/policy/`)
-   **`reference.py`**: The ideal reference implementation.
