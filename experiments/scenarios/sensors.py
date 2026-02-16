import numpy as np
from pydantic import BaseModel

class SensorConfig(BaseModel):
    sensor_id: str
    nominal_min: float
    nominal_max: float
    unit: str
    noise_std: float = 0.1
    base_value: float
    trend: float = 0.0 
    oscillation_amp: float = 0.0
    oscillation_period: float = 7.0

class EmulatedSensor:
    def __init__(self, config: SensorConfig, seed: int = 42):
        self.config = config
        self.rng = np.random.RandomState(seed)

    def generate_baseline(self, num_days: int = 7) -> np.ndarray:
        days = np.arange(num_days)
        signal = self.config.base_value + (self.config.trend * days)
        if self.config.oscillation_amp > 0:
            signal += self.config.oscillation_amp * np.sin(2 * np.pi * days / self.config.oscillation_period)
        noise = self.rng.normal(0, self.config.noise_std, size=num_days)
        return signal + noise

PH_CONFIG = SensorConfig(
    sensor_id="ph",
    nominal_min=9.5, nominal_max=10.5, unit="pH",
    base_value=10.0, noise_std=0.05, oscillation_amp=0.1
)

TEMP_CONFIG = SensorConfig(
    sensor_id="temp",
    nominal_min=25.0, nominal_max=38.0, unit="C",
    base_value=32.0, noise_std=0.5, oscillation_amp=1.0
)

EC_CONFIG = SensorConfig(
    sensor_id="ec",
    nominal_min=10.0, nominal_max=40.0, unit="mS/cm",
    base_value=25.0, noise_std=0.2
)

GROWTH_CONFIG = SensorConfig(
    sensor_id="growth",
    nominal_min=0.0, nominal_max=2.0, unit="OD",
    base_value=0.5, trend=0.15, noise_std=0.02
)
