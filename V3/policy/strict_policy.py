from typing import List, Optional
from core.types import ActionType, TrustAssessment, AutonomyMode
from core.interfaces import Policy

class StrictPolicy(Policy):
    """
    Implements a strict, monotonic trust policy.
    Maps TrustAssessment (Mode) -> Allowed Actions.
    """
    
    def get_allowed_actions(self, assessment: TrustAssessment) -> List[ActionType]:
        mode = assessment.autonomy_mode
        
        # 1. BLOCK: Only REQUEST_VERIFICATION and ALERT allowed.
        if mode == AutonomyMode.BLOCK:
            return [ActionType.REQUEST_VERIFICATION, ActionType.ALERT]
            
        # 2. SUGGEST_ONLY: No Active Actions (ACT_XX). Only Passive + Alert/Hold.
        if mode == AutonomyMode.SUGGEST_ONLY:
            return [ActionType.REQUEST_VERIFICATION, ActionType.ALERT, ActionType.HOLD]
            
        # 3. SAFE_ONLY: No risky optimizations. ACT_SAFE allowed.
        if mode == AutonomyMode.SAFE_ONLY:
            return [
                ActionType.REQUEST_VERIFICATION, 
                ActionType.ALERT, 
                ActionType.HOLD, 
                ActionType.ACT_SAFE
            ]
            
        # 4. FULL_AUTONOMY: All actions allowed.
        if mode == AutonomyMode.FULL_AUTONOMY:
            return list(ActionType)
            
        return []

    def check_compliance(self, action: ActionType, assessment: TrustAssessment) -> bool:
        allowed = self.get_allowed_actions(assessment)
        return action in allowed
