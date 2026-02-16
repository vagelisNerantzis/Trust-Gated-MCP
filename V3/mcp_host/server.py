from typing import Dict, Any, Optional
from core.interfaces import MCPHost
from core.types import (
    DailySensorSnapshot, ToolCallV1, HostPayloadV1, ActionType, AutonomyMode
)
from core.config import AppConfig
from trust_engine.engine import SpirulinaTrustEngine
from policy.strict_policy import StrictPolicy

class SpirulinaMCP_V3(MCPHost):
    def __init__(self, config: AppConfig):
        self.cfg = config
        self.trust_engine = SpirulinaTrustEngine(config.trust_engine)
        self.policy = StrictPolicy()
        
        self.current_snapshot: Optional[DailySensorSnapshot] = None
        self.prev_snapshot: Optional[DailySensorSnapshot] = None
        self.current_trust: Optional[Any] = None # Typed as TrustAssessment at runtime

    def update_state(self, snapshot: DailySensorSnapshot) -> None:
        self.prev_snapshot = self.current_snapshot
        self.current_snapshot = snapshot
        # Assess Trust Immediately
        self.current_trust = self.trust_engine.evaluate(self.current_snapshot, self.prev_snapshot)

    def get_context_payload(self) -> HostPayloadV1:
        if not self.current_snapshot or not self.current_trust:
             raise RuntimeError("System not initialized")
             
        # Flatten sensors for LLM
        sensor_data = {
            k: v.value if not v.is_missing else "MISSING"
            for k, v in self.current_snapshot.readings.items()
        }
        
        trust_data = {
            "score": round(self.current_trust.trust_score, 2),
            "mode": self.current_trust.autonomy_mode.value,
            "flags": [k for k, v in self.current_trust.flags.items() if v]
        }
        
        return HostPayloadV1(
            day=self.current_snapshot.day,
            sensor_context=sensor_data,
            trust_context=trust_data
        )

    def execute_tool(self, tool_call: ToolCallV1) -> Dict[str, Any]:
        """
        The TRUST GATE.
        Interprets ToolCallV1 -> Checks Policy -> Returns Result.
        """
        if not self.current_snapshot or not self.current_trust:
            return {"status": "ERROR", "message": "System not initialized"}

        # 1. Unpack Action
        if tool_call.tool_name != "execute_action":
            return {"status": "ERROR", "message": f"Unknown tool: {tool_call.tool_name}"}
            
        try:
            action_str = tool_call.arguments.get("action")
            rationale = tool_call.arguments.get("rationale", "")
            action = ActionType(action_str)
        except ValueError:
             return {"status": "ERROR", "message": f"Invalid action: {action_str}"}

        # 2. Policy Check (Compliance)
        allowed = self.policy.check_compliance(action, self.current_trust)

        # 2b. Host-authoritative execution semantics:
        # The MCP host (not main.py, not the LLM) decides what is actually executed.
        executed_action = action.value if allowed else ActionType.HOLD.value

        # 3. Construct Result
        msg = "Action executed successfully." if allowed else \
              f"Trust Mode is {self.current_trust.autonomy_mode.value}. Action {action.value} denied. Executed {executed_action} instead."
              
        return {
            "day": self.current_snapshot.day,
            "proposed_action": action.value,
            "executed_action": executed_action,
            "rationale": rationale,
            "trust_mode": self.current_trust.autonomy_mode.value,
            "trust_score": self.current_trust.trust_score,
            "status": "SUCCESS" if allowed else "BLOCKED",
            "message": msg,
            "override": (executed_action != action.value)
        }
