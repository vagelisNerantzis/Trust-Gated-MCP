from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

# --- Enums (Frozen Baseline) ---
class ActionType(str, Enum):
    HOLD = "HOLD"
    ALERT = "ALERT"
    REQUEST_VERIFICATION = "REQUEST_VERIFICATION"
    ACT_SAFE = "ACT_SAFE"
    ACT_UNRESTRICTED = "ACT_UNRESTRICTED"

class AutonomyMode(str, Enum):
    FULL_AUTONOMY = "FULL_AUTONOMY"
    SAFE_ONLY = "SAFE_ONLY"
    SUGGEST_ONLY = "SUGGEST_ONLY"
    BLOCK = "BLOCK"

# --- Sensor Data Models ---
class SensorReading(BaseModel):
    sensor_id: str
    timestamp_day: int
    value: float
    is_missing: bool = False

class DailySensorSnapshot(BaseModel):
    day: int
    readings: Dict[str, SensorReading]

# --- Trust Models ---
class TrustAssessment(BaseModel):
    day: int
    trust_score: float = Field(..., ge=0.0, le=1.0)
    autonomy_mode: AutonomyMode
    flags: Dict[str, bool]

# --- Contractual Schemas (V3 New) ---

class ToolCallV1(BaseModel):
    """Schema for Agent -> Host communication"""
    schema_version: str = "v1"
    tool_name: str  # e.g., "execute_action"
    arguments: Dict[str, Any] # e.g., {"action": "HOLD", "rationale": "..."}

class HostPayloadV1(BaseModel):
    """Schema for Host -> Agent communication"""
    schema_version: str = "v1"
    day: int
    sensor_context: Dict[str, Any] # Simplified readings
    trust_context: Dict[str, Any]  # Simplified trust info

class LogEvent(BaseModel):
    """Schema for experiment_log.csv row validity"""
    scenario_id: str
    day: int
    trust_score: float
    autonomy_mode: AutonomyMode
    flags: str
    llm_action: ActionType
    final_action: ActionType
    override: bool
    rationale: str
    parse_error: bool
