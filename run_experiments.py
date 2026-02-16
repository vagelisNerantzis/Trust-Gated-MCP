import sys
import os
import pandas as pd
import json
import ast

# Add project root to path
sys.path.append(os.getcwd())

from experiments.scenarios.generator import ScenarioGenerator
from experiments.mcp_server import SpirulinaMCP
from experiments.policy.reference import ReferencePolicy
from experiments.llm_agent.agent import LlmAgent
from experiments.core.types import FinalDecision, TrustAssessment, AgentProposal, ActionType

def main():
    print("Initializing Experiment Suite with MCP & LangChain...")
    
    # 1. Initialize Components
    generator = ScenarioGenerator()
    policy = ReferencePolicy() # Ground Truth Oracle
    mcp = SpirulinaMCP()       # The Trust Middleware Server
    agent = LlmAgent()         # The LangChain Agent
    
    print(f"Agent Backend: {agent.backend}")
    if agent.backend == "ollama":
        print(f"Model: {agent.ollama_model}")
    
    results = []
    scenarios = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    
    for sc_id in scenarios:
        print(f"Running {sc_id}...")
        scenario = generator.generate_scenario(sc_id)
        
        # Reset MCP state if needed (it keeps history but day updates matter)
        mcp = SpirulinaMCP() 
        prev_snapshot = None
        
        for snapshot in scenario.data:
            # 1. Update MCP State (Ingest Sensor Data)
            mcp.update_state(snapshot)
            trust = mcp.current_trust
            
            # 2. Agent Proposal (Agent calls MCP Tool)
            # proposal.action is what the Agent *Requested* via the tool
            proposal = agent.proposed_action(mcp)
            
            # 3. Check Real Outcome
            # Parse the MCP response stored in raw_output to see if BLOCKED
            mcp_result = {}
            actual_outcome = proposal.action # Default assumption
            
            if proposal.raw_output and proposal.raw_output.startswith("{"):
                try:
                    # Safe parse of the result dict
                    # It might be in 'raw_output' as stringified dict
                    mcp_result = ast.literal_eval(proposal.raw_output)
                    if mcp_result.get("status") == "BLOCKED":
                        # If blocked, effective action is HOLD/Safety
                        actual_outcome = ActionType.HOLD 
                except:
                    pass
            
            # 4. Reference Policy Check (Oracle)
            # What SHOULD have happened based on the Policy?
            policy_action = policy.evaluate(trust, proposal)
            
            # Override is true if the Agent's *intent* (proposal) contradicted the Policy
            # OR if the MCP had to Block it.
            override = (policy_action != proposal.action) or (actual_outcome != proposal.action)
            
            decision = FinalDecision(
                day=snapshot.day,
                trust_assessment=trust,
                proposed_action=proposal,
                final_action=actual_outcome, # The Result of the Gate
                policy_override=override,
                scenario_id=sc_id
            )
            results.append(decision)
            prev_snapshot = snapshot
            
    # Save Results
    output_dir = "experiments/logs"
    os.makedirs(output_dir, exist_ok=True)
    
    flat_data = []
    for r in results:
        row = {
            "scenario_id": r.scenario_id,
            "day": r.day,
            "trust_score": r.trust_assessment.trust_score,
            "autonomy_mode": r.trust_assessment.autonomy_mode.value,
            "flags": "|".join([k for k,v in r.trust_assessment.flags.items() if v]),
            "llm_action": r.proposed_action.action.value,
            "final_action": r.final_action.value,
            "override": r.policy_override,
            "rationale": r.proposed_action.rationale,
            "parse_error": r.proposed_action.parse_error,
            "raw_llm_output": r.proposed_action.raw_output,
            "backend": agent.backend
        }
        flat_data.append(row)
        
    df = pd.DataFrame(flat_data)
    df.to_csv(f"{output_dir}/experiment_log.csv", index=False)
    print(f"Completed. Logs saved to {output_dir}/experiment_log.csv")
    
    # Final Verification Summary
    total_steps = len(df)
    parse_errors = df["parse_error"].sum() if "parse_error" in df.columns else 0
    override_count = df["override"].sum()
    
    print("\n" + "="*40)
    print("FINAL EXPERIMENT SUMMARY (LangChain/MCP)")
    print("="*40)
    print(f"Backend Used:      {agent.backend}")
    print(f"Total Steps:       {total_steps}")
    print(f"Parse Errors:      {parse_errors}")
    print(f"Overrides:         {override_count}")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
