import random
import numpy as np
from typing import List, Dict, Any
from core.types import DailySensorSnapshot, SensorReading
from core.config import AppConfig

# --- Mock Sensor Configs (Simplified) ---
PH_BASE = {"mean": 10.0, "std": 0.05}
TEMP_BASE = {"mean": 32.0, "std": 0.5}
EC_BASE = {"mean": 1.5, "std": 0.1}
GROWTH_BASE = {"mean": 1.0, "std": 0.1}

class SeededGenerator:
    def __init__(self, config: AppConfig):
        self.cfg = config
        self.rng = random.Random(config.seeds.scenario_generation)
        self.np_rng = np.random.RandomState(config.seeds.scenario_generation)

    def _generate_baseline(self, days: int) -> Dict[str, List[float]]:
        data = {}
        for key, base in {"ph": PH_BASE, "temp": TEMP_BASE, "ec": EC_BASE, "growth": GROWTH_BASE}.items():
            noise = self.np_rng.normal(0, base["std"], days)
            values = base["mean"] + noise
            data[key] = values.tolist()
        return data

    def generate_scenario(self, scenario_id: str) -> List[DailySensorSnapshot]:
        days = self.cfg.scenarios.duration_days
        base_data = self._generate_baseline(days)
        snapshots = []
        
        # Inject Faults based on ID
        for d in range(days):
            readings = {}
            for sensor in ["ph", "temp", "ec", "growth"]:
                val = base_data[sensor][d]
                is_missing = False
                ts_day = d
                
                # --- Fault Injection Logic (Ported from V2) ---
                if scenario_id == "S2" and d == 3 and sensor == "ph":
                    val = 12.0 # Spike
                
                if scenario_id == "S3" and d >= 1 and sensor == "ph":
                    # Drift logic
                    shift = 0.05 * d
                    if d >= 3: shift = 0.14
                    val = 10.0 + shift

                if scenario_id == "S4" and d in [3, 4] and sensor == "ec":
                    is_missing = True
                
                if scenario_id == "S5" and d == 5:
                    if sensor == "growth": val = 1.2
                    if sensor == "temp": val = 20.0
                
                if scenario_id == "S6" and d == 4 and sensor == "ph":
                    ts_day = 2 # Timestamp anomaly

                if scenario_id == "S7" and d >= 2 and sensor == "ph":
                    val = 10.2

                if scenario_id == "S8":
                    if sensor == "ph" and d >= 2: val = 10.12 # Drift
                    if sensor == "ec" and d in [5, 6]: is_missing = True

                readings[sensor] = SensorReading(
                    sensor_id=sensor, 
                    timestamp_day=ts_day, 
                    value=val, 
                    is_missing=is_missing
                )
            snapshots.append(DailySensorSnapshot(day=d, readings=readings))
            
        return snapshots
