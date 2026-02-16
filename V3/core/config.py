from typing import List, Dict
import yaml
from pydantic import BaseModel, Field

class ProjectConfig(BaseModel):
    name: str
    version: str
    output_dir: str

class DeploymentConfig(BaseModel):
    mode: str
    llm_backend: str
    model_name: str

class ThresholdsConfig(BaseModel):
    z_score: float
    cusum_h: float
    cusum_k: float
    residual_growth: float

class PenaltiesConfig(BaseModel):
    timestamp_anomaly: float
    range_violation: float
    stale_data: float
    inconsistent_signals: float
    drift_suspected: float

class AutonomyLevels(BaseModel):
    full: float
    safe: float
    suggest: float
    block: float

class TrustEngineConfig(BaseModel):
    thresholds: ThresholdsConfig
    penalties: PenaltiesConfig
    autonomy_levels: AutonomyLevels

class SeedConfig(BaseModel):
    global_seed: int
    scenario_generation: int
    agent_noise: int
    evaluation_shuffle: int

class ScenariosConfig(BaseModel):
    duration_days: int
    active_scenarios: List[str]

class AppConfig(BaseModel):
    project: ProjectConfig
    deployment: DeploymentConfig
    trust_engine: TrustEngineConfig
    seeds: SeedConfig
    scenarios: ScenariosConfig

def load_config(path: str = "config/config.yaml") -> AppConfig:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    return AppConfig(**raw)
