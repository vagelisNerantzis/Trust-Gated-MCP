from typing import Protocol, List, Dict, Any
from .types import DailySensorSnapshot, TrustAssessment, ToolCallV1, ActionType

class TrustEngine(Protocol):
    """Interface for the Trust Calculation Engine"""
    def evaluate(self, snapshot: DailySensorSnapshot, prev_snapshot: DailySensorSnapshot | None) -> TrustAssessment:
        ...

class Policy(Protocol):
    """Interface for the Decision Policy (Compliance)"""
    def check_compliance(self, action: ActionType, assessment: TrustAssessment) -> bool:
        ...
    
    def get_allowed_actions(self, assessment: TrustAssessment) -> List[ActionType]:
        ...

class MCPHost(Protocol):
    """Interface for the MCP Server Orchestrator"""
    def update_state(self, snapshot: DailySensorSnapshot) -> None:
        ...
        
    def execute_tool(self, tool_call: ToolCallV1) -> Dict[str, Any]:
        ...
        
    def get_context_payload(self) -> Dict[str, Any]:
        ...
