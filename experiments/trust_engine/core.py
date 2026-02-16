from typing import List, Dict, Optional
from ..core.types import TrustAssessment, AutonomyMode, DailySensorSnapshot, SensorReading

class TrustEngine:
    """
    Trust Engine implementation for the Spirulina CPS.
    Evaluates sensor snapshots to produce a deterministic Trust Score.
    """
    # --- Scientific Constraints ---
    # Based on ISO/IEC/IEEE 42010 for System Verification
    
    # Z-Score Threshold (3-Sigma Rule)
    # Z = (x - mean) / std > 3.0 -> Statistical Outlier
    Z_SCORE_THRESHOLD = 3.0  
    
    # CUSUM Parameters (Cumulative Sum Control Chart)
    # Used for detecting small shifts (drift)
    CUSUM_K = 0.5   # Reference value (allowable slack)
    CUSUM_H = 5.0   # Decision Interval (Relaxed from 4.0 to prevent noise false positives)
    
    # Physics-Based Residual Threshold
    # |Growth_Actual - Growth_Expected| > Threshold
    RESIDUAL_THRESHOLD = 0.5 

    # --- Heuristic Penalties --- 
    # (Restored for scoring calculation)
    PENALTY_TIMESTAMP = 1.0   # Immediate Block
    PENALTY_RANGE = 0.5       # Major penalty (Safety)
    PENALTY_STALE = 0.6       # Major penalty (Availability)
    PENALTY_INCONSISTENT = 0.3 # Moderate penalty
    PENALTY_DRIFT = 0.2       # Minor penalty 

    def __init__(self):
        self.prev_trust_score = 1.0
        self.consecutive_missing_days = 0 
        
        # State Vector for CUSUM (Drift Detection)
        # S_pos: Positive cumulative deviation
        # S_neg: Negative cumulative deviation
        self.cusum_state = {
            "ph": {"S_pos": 0.0, "S_neg": 0.0}
        }
        
        # Baselines from sensor configuration (Nominal Operations)
        self.baselines = {
             "ph": {"mean": 10.0, "std": 0.05},
             "temp": {"mean": 32.0, "std": 0.5}
        }

    def evaluate(self, snapshot: DailySensorSnapshot, prev_snapshot: Optional[DailySensorSnapshot]) -> TrustAssessment:
        flags: Dict[str, bool] = {
            "range_violation": False,
            "drift_suspected": False,
            "stale_data": False,
            "timestamp_anomaly": False,
            "inconsistent_signals": False
        }
        
        # 1. Watchdog Timer (Stale Data Detection)
        # Implementation: Counter-based heartbeat monitoring
        missing_count = sum(1 for s in snapshot.readings.values() if s.is_missing)
        
        if missing_count > 0:
            self.consecutive_missing_days += 1
        else:
            self.consecutive_missing_days = 0 

        if self.consecutive_missing_days >= 2:
            flags["stale_data"] = True
            
        # 2. Timestamp Consistency Check
        # Verification of Temporal Integrity
        for reading in snapshot.readings.values():
            if not reading.is_missing and reading.timestamp_day != snapshot.day:
                flags["timestamp_anomaly"] = True
                break
             
        # 3. Z-Score Analysis (Spike / Outlier Detection)
        # Statistical outlier detection using 3-sigma rule (Z > 3.0)
        # Applied to all sensors with known Gaussian baselines
        for sensor_id, baseline in self.baselines.items():
            reading = snapshot.readings.get(sensor_id)
            if reading and not reading.is_missing:
                mu = baseline["mean"]
                sigma = baseline["std"]
                z_score = (reading.value - mu) / sigma
                
                if abs(z_score) > self.Z_SCORE_THRESHOLD:
                    flags["range_violation"] = True
                    break # One violation is enough to flag the snapshot
        
        # 4. CUSUM Analysis (Drift Detection)
        # Cumulative Sum Control Chart algorithm for detecting mean shifts
        ph_reading = snapshot.readings.get("ph")
        if ph_reading and not ph_reading.is_missing and not flags["range_violation"]:
            val = ph_reading.value
            mu = self.baselines["ph"]["mean"]
            sigma = self.baselines["ph"]["std"] # Normalize scale
            
            # Standardized deviation
            z = (val - mu) / sigma
            
            # Update CUSUM accumulators
            s_pos = max(0, self.cusum_state["ph"]["S_pos"] + z - self.CUSUM_K)
            s_neg = max(0, self.cusum_state["ph"]["S_neg"] - z - self.CUSUM_K)
            
            self.cusum_state["ph"]["S_pos"] = s_pos
            self.cusum_state["ph"]["S_neg"] = s_neg
            
            if s_pos > self.CUSUM_H or s_neg > self.CUSUM_H:
                flags["drift_suspected"] = True
                
        # 5. Physics-Based Residual Analysis (Inconsistency Detection)
        # Logic: Growth Rate is functionally dependent on Temperature.
        # Theoretical Model: Optimal T=32C. If T < 25C, Growth should be near 0.
        # Residual = |Growth_Observed - Growth_Predicted|
        
        growth = snapshot.readings.get("growth")
        temp = snapshot.readings.get("temp")
        
        if growth and temp and not growth.is_missing and not temp.is_missing:
             # Simplified Physics Model: 
             # If Temp < 28.0 (Cold Stress), Max Growth should be < 0.8
             if temp.value < 28.0:
                 expected_max_growth = 0.8
                 if growth.value > expected_max_growth:
                     # Residual is significant
                     flags["inconsistent_signals"] = True

        # 6. Calculate Trust Score (Deterministically)
        score = 1.0
        
        if flags["timestamp_anomaly"]: score -= self.PENALTY_TIMESTAMP
        if flags["range_violation"]: score -= self.PENALTY_RANGE
        if flags["stale_data"]: score -= self.PENALTY_STALE
        if flags["drift_suspected"]: score -= self.PENALTY_DRIFT
        if flags["inconsistent_signals"]: score -= self.PENALTY_INCONSISTENT
        
        # Missing data decay on existing score
        if missing_count > 0:
            score = min(score, self.prev_trust_score * 0.8)
            
        score = max(0.0, min(1.0, score))
        self.prev_trust_score = score
        
        # 7. Autonomy Mode Mapping
        if score >= 0.8:
            mode = AutonomyMode.FULL_AUTONOMY
        elif score >= 0.6:
            mode = AutonomyMode.SAFE_ONLY
        elif score >= 0.4:
            mode = AutonomyMode.SUGGEST_ONLY
        else:
            mode = AutonomyMode.BLOCK
            
        return TrustAssessment(
            day=snapshot.day,
            trust_score=score,
            autonomy_mode=mode,
            flags=flags
        )
