from typing import Any, Dict, List, Optional
import json
from pydantic import BaseModel, Field

from .core.types import (
    DailySensorSnapshot, 
    TrustAssessment, 
    ActionType, 
    AutonomyMode
)
from .trust_engine.core import TrustEngine
from .policy.reference import ReferencePolicy

class SpirulinaMCP:
    """
    Simulates a Model Context Protocol (MCP) Server that manages
    access to the Spirulina Bioreactor.
    
    Acts as a 'Trust Middleware':
    1. Holds the current state (Sensor Snapshot).
    2. Exposes Resources (Sensor Data).
    3. Exposes Tools (Actions).
    4. GATES all Tool calls via the TrustEngine.
    """
    
    def __init__(self):
        self.trust_engine = TrustEngine()
        # Reference Policy for logging/comparison, though the Gate uses TrustEngine modes
        self.policy = ReferencePolicy() 
        
        self.current_snapshot: Optional[DailySensorSnapshot] = None
        self.prev_snapshot: Optional[DailySensorSnapshot] = None
        self.current_trust: Optional[TrustAssessment] = None
        self._last_action_result: Dict[str, Any] = {}

    def update_state(self, snapshot: DailySensorSnapshot):
        """
        Updates the server state with the new daily snapshot.
        This represents the 'Real Time' data ingest.
        """
        self.prev_snapshot = self.current_snapshot
        self.current_snapshot = snapshot
        
        # Pre-calculate trust for the Gating Mechanism
        self.current_trust = self.trust_engine.evaluate(self.current_snapshot, self.prev_snapshot)

    def list_resources(self) -> List[Dict[str, str]]:
        """MCP Prototype: List available resources."""
        if not self.current_snapshot:
            return []
        return [
            {
                "uri": f"sensors://{self.current_snapshot.day}/readings",
                "name": f"Sensor Readings Day {self.current_snapshot.day}",
                "mimeType": "application/json"
            },
            {
                "uri": f"trust://{self.current_snapshot.day}/score",
                "name": f"Trust Score Day {self.current_snapshot.day}",
                "mimeType": "application/json"
            }
        ]

    def read_resource(self, uri: str) -> str:
        """MCP Prototype: Read a resource."""
        if not self.current_snapshot:
             return json.dumps({"error": "No data available"})
             
        if "sensors://" in uri:
            # Flatten readings for easier LLM consumption
            data = {
                "day": self.current_snapshot.day,
                "sensors": {
                    k: v.value if not v.is_missing else "MISSING"
                    for k, v in self.current_snapshot.readings.items()
                }
            }
            return json.dumps(data, indent=2)
            
        if "trust://" in uri:
            # Reveal trust score? 
            # In a strict setting, maybe hidden. For this experiment, transparent.
            data = {
                "score": round(self.current_trust.trust_score, 2),
                "mode": self.current_trust.autonomy_mode.value,
                "flags": self.current_trust.flags
            }
            return json.dumps(data, indent=2)
            
        return json.dumps({"error": "Resource not found"})

    def execute_action(self, action: ActionType, rationale: str) -> Dict[str, Any]:
        """
        TRUST-GATED TOOL
        
        The Agent calls this tool to execute an action.
        The Middleware (this code) checks the Trust Score/Mode via TrustEngine.
        If the Mode prohibits the Action, it returns "BLOCKED".
        """
        if not self.current_snapshot or not self.current_trust:
            return {"status": "ERROR", "message": "System not initialized"}
            
        mode = self.current_trust.autonomy_mode
        allowed = False
        message = ""
        
        # --- The Trust Gate Logic ---
        # 1. BLOCK Mode: Only REQUEST_VERIFICATION allowed (or Alert)
        if mode == AutonomyMode.BLOCK:
            if action in [ActionType.REQUEST_VERIFICATION, ActionType.ALERT]:
                allowed = True
            else:
                allowed = False
                message = f"Trust Mode is BLOCK. Action {action.value} denied. Only REQUEST_VERIFICATION allowed."

        # 2. SUGGEST_ONLY: Alerts/Requests allowed. Active control denied.
        elif mode == AutonomyMode.SUGGEST_ONLY:
            if action in [ActionType.REQUEST_VERIFICATION, ActionType.ALERT, ActionType.HOLD]:
                 allowed = True
            else:
                 allowed = False
                 # Note: S2/S7 might want ALERT.
                 message = f"Trust Mode is SUGGEST_ONLY. Action {action.value} denied. Active control restricted."

        # 3. SAFE_ONLY: Safe actions allowed. Restricted (Optimization) denied.
        elif mode == AutonomyMode.SAFE_ONLY:
            if action == ActionType.ACT_RESTRICTED:
                allowed = False
                message = f"Trust Mode is SAFE_ONLY. Optimization (ACT_RESTRICTED) denied."
            else:
                allowed = True
        
        # 4. FULL_AUTONOMY: Everything allowed.
        elif mode == AutonomyMode.FULL_AUTONOMY:
            allowed = True
            
        # --- Execution ---
        result = {
            "day": self.current_snapshot.day,
            "proposed_action": action.value,
            "rationale": rationale,
            "trust_mode": mode.value,
            "trust_score": self.current_trust.trust_score,
            "status": "SUCCESS" if allowed else "BLOCKED",
            "message": message if not allowed else "Action executed successfully."
        }
        
        self._last_action_result = result
        return result
