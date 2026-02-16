from ..core.types import ActionType, AutonomyMode, TrustAssessment, AgentProposal

class ReferencePolicy:
    """
    Deterministic Ground Truth Policy.
    Evaluates trust state and flags to determine the mandatory action.
    """
    
    def evaluate(self, assessment: TrustAssessment, proposal: AgentProposal) -> ActionType:
        # Priority 1: Low Trust
        if assessment.trust_score < 0.4:
            return ActionType.REQUEST_VERIFICATION
            
        flags = assessment.flags
        
        # Priority 2: Safety Critical Flags
        if flags.get("range_violation"):
            return ActionType.ALERT
            
        if flags.get("stale_data"):
            return ActionType.REQUEST_VERIFICATION
            
        if flags.get("timestamp_anomaly"):
            return ActionType.ALERT
            
        # Priority 3: Operational Warnings
        if flags.get("drift_suspected"):
            return ActionType.HOLD
            
        if flags.get("inconsistent_signals"):
            return ActionType.HOLD
            
        # Priority 4: Mode Constraints
        mode = assessment.autonomy_mode
        proposed = proposal.action
        
        if mode == AutonomyMode.SAFE_ONLY:
            if proposed in [ActionType.ACT_SAFE, ActionType.HOLD]:
                return proposed
            else:
                return ActionType.ACT_SAFE 
                
        # Priority 5: Full Autonomy
        if proposed == ActionType.ACT_RESTRICTED:
            if assessment.trust_score >= 0.8 and not any(flags.values()):
                return ActionType.ACT_RESTRICTED
            else:
                return ActionType.ACT_SAFE
        
        return proposed
