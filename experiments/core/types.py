from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

# --- Actions ---
class ActionType(str, Enum):
    HOLD = "HOLD"
    ALERT = "ALERT"
    REQUEST_VERIFICATION = "REQUEST_VERIFICATION"
    ACT_SAFE = "ACT_SAFE"
    ACT_RESTRICTED = "ACT_RESTRICTED"

# --- Autonomy Modes ---
class AutonomyMode(str, Enum):
    FULL_AUTONOMY = "FULL_AUTONOMY"  # Trust >= 0.8
    SAFE_ONLY = "SAFE_ONLY"          # 0.6 <= Trust < 0.8
    SUGGEST_ONLY = "SUGGEST_ONLY"    # 0.4 <= Trust < 0.6
    BLOCK = "BLOCK"                  # Trust < 0.4

# --- Sensor Data ---
class SensorReading(BaseModel):
    sensor_id: str
    timestamp_day: int
    value: float
    is_missing: bool = False
    is_corrupted: bool = False
    
    model_config = ConfigDict(frozen=True)

class DailySensorSnapshot(BaseModel):
    day: int
    readings: Dict[str, SensorReading]

# --- Trust Engine Output ---
class TrustAssessment(BaseModel):
    day: int
    trust_score: float = Field(..., ge=0.0, le=1.0)
    autonomy_mode: AutonomyMode
    flags: Dict[str, bool] = Field(default_factory=dict)

# --- LLM & Policy Data ---
class AgentProposal(BaseModel):
    action: ActionType
    rationale: str
    raw_output: str = ""
    parse_error: bool = False

class FinalDecision(BaseModel):
    day: int
    trust_assessment: TrustAssessment
    proposed_action: Optional[AgentProposal]
    final_action: ActionType
    policy_override: bool
    scenario_id: str

# --- Ground Truth & Scenario Definition ---
class GroundTruth(BaseModel):
    day: int
    expected_flags: Dict[str, bool]
    expected_autonomy: AutonomyMode
    expected_action: ActionType

class Scenario(BaseModel):
    id: str
    name: str
    description: str
    data: List[DailySensorSnapshot]
    ground_truths: List[GroundTruth]
