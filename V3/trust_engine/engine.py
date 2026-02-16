from typing import Dict, Optional, Any
from core.types import DailySensorSnapshot, TrustAssessment, AutonomyMode
from core.config import TrustEngineConfig
from .detections import check_z_score, update_cusum, check_stale, check_physics_residual

class SpirulinaTrustEngine:
    def __init__(self, config: TrustEngineConfig):
        self.cfg = config
        self.prev_trust_score = 1.0
        self.consecutive_missing = 0
        # CUSUM State
        self.cusum_state = {"S_pos": 0.0, "S_neg": 0.0}
        # Baselines (Hardcoded or Config-injected)
        self.baselines = {
             "ph": {"mean": 10.0, "std": 0.05},
             "temp": {"mean": 32.0, "std": 0.5}
        }

    def evaluate(self, snapshot: DailySensorSnapshot, prev_snapshot: Optional[DailySensorSnapshot]) -> TrustAssessment:
        flags = {
            "range_violation": False,
            "drift_suspected": False,
            "stale_data": False,
            "timestamp_anomaly": False,
            "inconsistent_signals": False
        }

        # 1. Stale Data
        missing = sum(1 for s in snapshot.readings.values() if s.is_missing)
        if missing > 0: self.consecutive_missing += 1
        else: self.consecutive_missing = 0
        
        if check_stale(self.consecutive_missing, 2):
            flags["stale_data"] = True

        # 2. Timestamp Anomaly
        for r in snapshot.readings.values():
            if not r.is_missing and r.timestamp_day != snapshot.day:
                flags["timestamp_anomaly"] = True

        # 3. Z-Score (Range)
        for sid, base in self.baselines.items():
            r = snapshot.readings.get(sid)
            if r and not r.is_missing:
                if check_z_score(r.value, base["mean"], base["std"], self.cfg.thresholds.z_score):
                    flags["range_violation"] = True

        # 4. CUSUM (Drift) - pH only
        ph = snapshot.readings.get("ph")
        if ph and not ph.is_missing and not flags["range_violation"]:
            drift, sp, sn = update_cusum(
                ph.value, 
                self.baselines["ph"]["mean"], 
                self.baselines["ph"]["std"], 
                self.cfg.thresholds.cusum_k, 
                self.cfg.thresholds.cusum_h,
                self.cusum_state["S_pos"],
                self.cusum_state["S_neg"]
            )
            self.cusum_state["S_pos"] = sp
            self.cusum_state["S_neg"] = sn
            if drift: 
                flags["drift_suspected"] = True

        # 5. Physics Residuals
        growth = snapshot.readings.get("growth")
        temp = snapshot.readings.get("temp")
        if growth and temp and not growth.is_missing and not temp.is_missing:
             # Condition: Temp < 28.0. Threshold: Growth > 0.8
             if check_physics_residual(growth.value, temp.value, 0.8, temp.value < 28.0):
                 flags["inconsistent_signals"] = True

        # 6. Score Calculation
        score = 1.0
        if flags["timestamp_anomaly"]: score -= self.cfg.penalties.timestamp_anomaly
        if flags["range_violation"]: score -= self.cfg.penalties.range_violation
        if flags["stale_data"]: score -= self.cfg.penalties.stale_data
        if flags["drift_suspected"]: score -= self.cfg.penalties.drift_suspected
        if flags["inconsistent_signals"]: score -= self.cfg.penalties.inconsistent_signals
        
        if missing > 0:
            score = min(score, self.prev_trust_score * 0.8)

        score = max(0.0, min(1.0, score))
        self.prev_trust_score = score

        # 7. Autonomy Mode Mapping
        if score >= self.cfg.autonomy_levels.full: mode = AutonomyMode.FULL_AUTONOMY
        elif score >= self.cfg.autonomy_levels.safe: mode = AutonomyMode.SAFE_ONLY
        elif score >= self.cfg.autonomy_levels.suggest: mode = AutonomyMode.SUGGEST_ONLY
        else: mode = AutonomyMode.BLOCK

        return TrustAssessment(day=snapshot.day, trust_score=score, autonomy_mode=mode, flags=flags)
