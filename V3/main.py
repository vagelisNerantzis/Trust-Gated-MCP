import sys
import os
import csv
from datetime import datetime

# Allow importing from current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import load_config
from core.types import ToolCallV1, ActionType
from core.logging import ExperimentLogger
from simulation.generator import SeededGenerator
from mcp_host.server import SpirulinaMCP_V3
from clients.llm_agent import LlmAgent

# --- Mock Agent Adapter (For Regression) ---
# In a full deployment, this would be an Ollama Client
class MockAgent:
    def __init__(self, seed: int):
        self.seed = seed
    
    def decide(self, payload) -> ToolCallV1:
        # Simple Logic: Always Optimize unless Trust < 0.4
        trust = payload.trust_context
        score = trust["score"]
        
        action = ActionType.ACT_UNRESTRICTED
        if score < 0.4:
            action = ActionType.REQUEST_VERIFICATION
            
        return ToolCallV1(
            tool_name="execute_action",
            arguments={"action": action.value, "rationale": "Mock Agent Logic"}
        )

def main():
    try:
        print("Starting Main...", flush=True)
        # 1. Load Config
        cfg = load_config("c:/GitFolders/TrustGatedMCP_V2/V3/config/config.yaml")
        print("Config Loaded.", flush=True)
        
        # 2. Setup Logging
        os.makedirs(cfg.project.output_dir, exist_ok=True)
        log_path = os.path.join(cfg.project.output_dir, "experiment_log.csv")
        print(f"Log Path: {log_path}", flush=True)
        
        # 3. Initialize Components
        gen = SeededGenerator(cfg)
        host = SpirulinaMCP_V3(cfg)
        
        # Select Agent Logic
        llm_backend = os.environ.get("LLM_BACKEND", cfg.deployment.llm_backend).lower()
        if llm_backend == "ollama":
            agent = LlmAgent(cfg, cfg.seeds.agent_noise)
        else:
            agent = MockAgent(cfg.seeds.agent_noise)
            print(f"Using MockAgent (backend={llm_backend})", flush=True)
            
        print("Components Initialized.", flush=True)
        
        # 4. Run Loop
        print("Starting Loop...", flush=True)
        
        # Resolve Backend/Model and Logging Context
        with ExperimentLogger(cfg) as logger:
            print(f"Log file opened at {logger.log_path}", flush=True)
            
            for sc_id in cfg.scenarios.active_scenarios:
                print(f"Running Scenario: {sc_id}", flush=True)
                snapshots = gen.generate_scenario(sc_id)
                host.current_snapshot = None # Reset
                
                for snap in snapshots:
                    # Update Host (Sensor Ingest)
                    host.update_state(snap)
                    
                    # Get Context
                    payload = host.get_context_payload()
                    
                    # Agent Decide
                    tool_call = agent.decide(payload)
                    
                    # Execute (Trust Gate)
                    result = host.execute_tool(tool_call)
                    
                    # Determine Executed Action
                    # Robustness: Handle missing proposal
                    proposed = result.get("proposed_action", "UNKNOWN_PROPOSAL")
                    is_blocked = (result.get("status") == "BLOCKED")
                    # If blocked, we default to HOLD (Safe Fallback)
                    executed = "HOLD" if is_blocked else proposed
                    
                    # Log
                    flags_str = "|".join([k for k,v in host.current_trust.flags.items() if v])
                    print(f"  [Day {snap.day}] Trust={result['trust_score']:.2f} Action={executed}", flush=True)
                    logger.log_result(
                        scenario_id=sc_id, 
                        day=snap.day,
                        trust_score=result["trust_score"], 
                        mode=result["trust_mode"], 
                        flags=flags_str,
                        proposed_action=proposed,
                        executed_action=executed,
                        status=result["status"],
                        override=result["override"],
                        model_digest=""
                    )
        print("Done.", flush=True)
    except Exception as e:
        print(f"CRITICAL ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
