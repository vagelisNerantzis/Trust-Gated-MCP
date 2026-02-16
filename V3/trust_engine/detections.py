import numpy as np

# --- Pure Functional Detectors ---

def check_z_score(value: float, mean: float, std: float, threshold: float) -> bool:
    """Detects statistical outliers using Z-Score."""
    if std == 0: return False
    z = (value - mean) / std
    return abs(z) > threshold

def update_cusum(value: float, mean: float, std: float, k: float, h: float, s_pos: float, s_neg: float) -> tuple[bool, float, float]:
    """Updates CUSUM state and checks for drift."""
    if std == 0: return False, s_pos, s_neg
    
    z = (value - mean) / std
    s_pos_new = max(0, s_pos + z - k)
    s_neg_new = max(0, s_neg - z - k)
    
    drift_detected = (s_pos_new > h) or (s_neg_new > h)
    return drift_detected, s_pos_new, s_neg_new

def check_physics_residual(val_a: float, val_b: float, threshold: float, condition: bool) -> bool:
    """Checks physics consistency (e.g., Growth vs Temp)."""
    # Logic: If condition (Temp < 28) is met, Residual check applies.
    if condition:
        # Simplified: expected max growth 0.8. If actual > 0.8 -> Residual high.
        return val_a > threshold # val_a is growth
    return False

def check_stale(missing_counter: int, limit: int) -> bool:
    """Checks for stale data availability."""
    return missing_counter >= limit
