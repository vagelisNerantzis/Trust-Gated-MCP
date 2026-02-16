import unittest
from core.types import DailySensorSnapshot, SensorReading
from core.config import TrustEngineConfig, ThresholdsConfig, PenaltiesConfig, AutonomyLevels
from trust_engine.engine import SpirulinaTrustEngine

class TestTrustEngine(unittest.TestCase):
    def setUp(self):
        # Mock Config
        self.cfg = TrustEngineConfig(
            thresholds=ThresholdsConfig(z_score=3.0, cusum_h=5.0, cusum_k=0.5, residual_growth=0.5),
            penalties=PenaltiesConfig(timestamp_anomaly=1.0, range_violation=0.5, stale_data=0.6, inconsistent_signals=0.3, drift_suspected=0.2),
            autonomy_levels=AutonomyLevels(full=0.8, safe=0.6, suggest=0.4, block=0.0)
        )
        self.engine = SpirulinaTrustEngine(self.cfg)

    def test_clean_snapshot(self):
        # Create a PERFECT snapshot
        readings = {
            "ph": SensorReading(sensor_id="ph", timestamp_day=1, value=10.0),
            "temp": SensorReading(sensor_id="temp", timestamp_day=1, value=32.0),
            "ec": SensorReading(sensor_id="ec", timestamp_day=1, value=1.5),
            "growth": SensorReading(sensor_id="growth", timestamp_day=1, value=1.0)
        }
        snap = DailySensorSnapshot(day=1, readings=readings)
        
        assessment = self.engine.evaluate(snap, None)
        self.assertEqual(assessment.trust_score, 1.0)
        self.assertEqual(len([k for k,v in assessment.flags.items() if v]), 0)

    def test_range_violation(self):
        # pH Spike to 12.0
        readings = {
             "ph": SensorReading(sensor_id="ph", timestamp_day=1, value=12.0), # Mean 10, Std 0.05 -> HUGE Z
             "temp": SensorReading(sensor_id="temp", timestamp_day=1, value=32.0)
        }
        snap = DailySensorSnapshot(day=1, readings=readings)
        assessment = self.engine.evaluate(snap, None)
        
        self.assertTrue(assessment.flags["range_violation"])
        self.assertEqual(assessment.trust_score, 0.5)

if __name__ == '__main__':
    unittest.main()
