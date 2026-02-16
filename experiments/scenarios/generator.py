import numpy as np
from typing import List, Dict
from ..core.types import (
    Scenario, DailySensorSnapshot, SensorReading, GroundTruth, 
    AutonomyMode, ActionType
)
from .sensors import (
    EmulatedSensor, PH_CONFIG, TEMP_CONFIG, EC_CONFIG, GROWTH_CONFIG
)

class ScenarioGenerator:
    def __init__(self):
        self.base_sensors = {
            "ph": EmulatedSensor(PH_CONFIG),
            "temp": EmulatedSensor(TEMP_CONFIG),
            "ec": EmulatedSensor(EC_CONFIG),
            "growth": EmulatedSensor(GROWTH_CONFIG)
        }

    def _create_clean_snapshots(self, seed: int = 42) -> List[DailySensorSnapshot]:
        snapshots = []
        sensors = {
            # Fix: v is an EmulatedSensor, so we must use v.config
            k: EmulatedSensor(v.config, seed=seed+i) for i, (k, v) in enumerate(self.base_sensors.items())
        }
        days_n = 7
        data = {k: s.generate_baseline(days_n) for k, s in sensors.items()}
        
        for d in range(days_n):
            readings = {}
            for k in sensors:
                readings[k] = SensorReading(
                    sensor_id=k,
                    timestamp_day=d,
                    value=data[k][d]
                )
            snapshots.append(DailySensorSnapshot(day=d, readings=readings))
        return snapshots

    def generate_scenario(self, scenario_type: str) -> Scenario:
        snapshots = self._create_clean_snapshots(seed=42)
        ground_truths = []
        
        if scenario_type == "S1":
            # Clean Baseline
            name = "S1 – Clean Baseline"
            desc = "Nominal operation, high trust."
            for s in snapshots:
                ground_truths.append(GroundTruth(
                    day=s.day,
                    expected_flags={},
                    expected_autonomy=AutonomyMode.FULL_AUTONOMY,
                    expected_action=ActionType.ACT_RESTRICTED # Mock Agent proposes Restricted, Policy Allows it
                ))

        elif scenario_type == "S2":
            # pH Spike
            name = "S2 – pH Spike"
            desc = "Day 3 pH spikes to 12.0."
            for s in snapshots:
                expected_flags = {}
                mode = AutonomyMode.FULL_AUTONOMY
                action = ActionType.ACT_RESTRICTED
                
                if s.day == 3:
                     s.readings["ph"] = SensorReading(
                         sensor_id="ph", timestamp_day=s.day, value=12.0
                     )
                     expected_flags = {"range_violation": True}
                     mode = AutonomyMode.SUGGEST_ONLY
                     action = ActionType.ALERT

                ground_truths.append(GroundTruth(
                    day=s.day,
                    expected_flags=expected_flags,
                    expected_autonomy=mode,
                    expected_action=action
                ))

        elif scenario_type == "S3":
            # pH Drift
            # Z-Score Limit (Mean 10.0, Std 0.05) is 10.15 (Z=3).
            # We want to trigger CUSUM (H=5.0) WITHOUT triggering Z-Score.
            name = "S3 – Slow pH Drift"
            desc = "pH drifts to 10.14, triggering CUSUM."
            for s in snapshots:
                expected_flags = {}
                mode = AutonomyMode.FULL_AUTONOMY
                action = ActionType.ACT_RESTRICTED
                
                # Careful Tuning for CUSUM H=5.0
                # Day 0: 10.0 (Z=0)
                # Day 1: 10.05 (Z=1) -> S=0.5
                # Day 2: 10.10 (Z=2) -> S=0.5 + 1.5 = 2.0
                # Day 3: 10.14 (Z=2.8) -> S=2.0 + 2.3 = 4.3 (Close, maybe not 5.0 yet)
                # Day 4: 10.14 (Z=2.8) -> S=4.3 + 2.3 = 6.6 > 5.0 (TRIGGER)
                
                # Let's force values
                val = 10.0
                if s.day == 1: val = 10.05
                if s.day == 2: val = 10.10
                if s.day >= 3: val = 10.14
                
                s.readings["ph"] = s.readings["ph"].model_copy(update={"value": val})
                
                if s.day >= 4: 
                     expected_flags["drift_suspected"] = True
                     mode = AutonomyMode.FULL_AUTONOMY 
                     action = ActionType.HOLD 
                
                ground_truths.append(GroundTruth(
                    day=s.day, 
                    expected_flags=expected_flags,
                    expected_autonomy=mode,
                    expected_action=action
                ))

        elif scenario_type == "S4":
            # EC Dropout
            name = "S4 – EC Dropout"
            desc = "EC sensor missing Days 3, 4."
            for s in snapshots:
                expected_flags = {}
                mode = AutonomyMode.FULL_AUTONOMY
                action = ActionType.ACT_RESTRICTED
                
                if s.day in [3, 4]:
                    s.readings["ec"] = s.readings["ec"].model_copy(update={"is_missing": True})
                
                if s.day == 3:
                     # Agent logic: Trust 0.8 < 0.9. Proposes ACT_RESTRICTED.
                     action = ActionType.ACT_RESTRICTED

                if s.day == 4:
                     expected_flags["stale_data"] = True
                     mode = AutonomyMode.SUGGEST_ONLY
                     # Mock agent in 'mock' mode defaults to HOLD now for safety? 
                     # Or the scenario expects REQUEST_VERIFICATION.
                     # Previous hardcoded expectation was REQUEST_VERIFICATION.
                     action = ActionType.REQUEST_VERIFICATION
                
                ground_truths.append(GroundTruth(day=s.day, expected_flags=expected_flags, expected_autonomy=mode, expected_action=action))

        elif scenario_type == "S5":
            # Inconsistency
            name = "S5 – Inconsistency"
            desc = "Growth High, Temp Low."
            for s in snapshots:
                expected_flags = {}
                mode = AutonomyMode.FULL_AUTONOMY
                action = ActionType.ACT_RESTRICTED
                
                if s.day == 5:
                    s.readings["growth"] = s.readings["growth"].model_copy(update={"value": 1.2})
                    s.readings["temp"] = s.readings["temp"].model_copy(update={"value": 20.0}) 
                    # Temp 20 is < 25 -> Range Violation (Z-Score high for Temp) AND Inconsistent.
                    # Temp Mean 32, Std 0.5. Value 20 is Z=24!! Explicit Range Violation.
                    expected_flags = {"range_violation": True, "inconsistent_signals": True}
                    mode = AutonomyMode.BLOCK 
                    action = ActionType.REQUEST_VERIFICATION 
                    
                ground_truths.append(GroundTruth(day=s.day, expected_flags=expected_flags, expected_autonomy=mode, expected_action=action))

        elif scenario_type == "S6":
            # Timestamp Anomaly
            name = "S6 – Timestamp Anomaly"
            desc = "Day 4 reading reports Day 2 timestamp."
            for s in snapshots:
                expected_flags = {}
                mode = AutonomyMode.FULL_AUTONOMY
                action = ActionType.ACT_RESTRICTED
                
                if s.day == 4:
                    s.readings["ph"] = s.readings["ph"].model_copy(update={"timestamp_day": 2})
                    expected_flags["timestamp_anomaly"] = True
                    mode = AutonomyMode.BLOCK 
                    action = ActionType.ALERT 
                    
                ground_truths.append(GroundTruth(day=s.day, expected_flags=expected_flags, expected_autonomy=mode, expected_action=action))
                
        elif scenario_type == "S7":
            # Borderline High pH -> Now Statistical Outlier
            name = "S7 – Statistical Outlier (Z-Score)"
            desc = "pH 10.2 (Z=4.0). Triggers Range Violation."
            for s in snapshots:
                expected_flags = {}
                mode = AutonomyMode.FULL_AUTONOMY
                action = ActionType.ACT_RESTRICTED
                
                if s.day >= 2:
                    s.readings["ph"] = s.readings["ph"].model_copy(update={"value": 10.2})
                    # pH 10.2 > 10.15 (Z=3).
                    expected_flags["range_violation"] = True
                    mode = AutonomyMode.SUGGEST_ONLY # Trust drops
                    action = ActionType.ALERT 
                
                ground_truths.append(GroundTruth(day=s.day, expected_flags=expected_flags, expected_autonomy=mode, expected_action=action))

        elif scenario_type == "S8":
            # Mixed (Drift + Dropout)
            name = "S8 – Mixed Degradation"
            desc = "Drifting pH (CUSUM) AND missing EC."
            for s in snapshots:
                expected_flags = {}
                mode = AutonomyMode.FULL_AUTONOMY
                action = ActionType.ACT_RESTRICTED 
                
                # Drift: pH 10.12 (Z=2.4 < 3.0), but CUSUM accumulates.
                s.readings["ph"] = s.readings["ph"].model_copy(update={"value": 10.12})
                
                # CUSUM triggers immediately/soon (Day 0: S_pos=1.9, Day 1: 3.8, Day 2: 5.7 > 4.0)
                if s.day >= 2:
                    expected_flags["drift_suspected"] = True
                    action = ActionType.HOLD
                
                if s.day in [5, 6]:
                     s.readings["ec"] = s.readings["ec"].model_copy(update={"is_missing": True})
                
                if s.day == 5:
                    mode = AutonomyMode.SAFE_ONLY
                    action = ActionType.HOLD # Drift overrides Safe
                
                if s.day == 6:
                    expected_flags["stale_data"] = True
                    mode = AutonomyMode.BLOCK 
                    action = ActionType.REQUEST_VERIFICATION
                
                ground_truths.append(GroundTruth(day=s.day, expected_flags=expected_flags, expected_autonomy=mode, expected_action=action))
        
        else:
            raise ValueError(f"Unknown scenario {scenario_type}")
            
        return Scenario(id=scenario_type, name=name, description=desc, data=snapshots, ground_truths=ground_truths)
