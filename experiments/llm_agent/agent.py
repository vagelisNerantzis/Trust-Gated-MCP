import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
try:
    from langchain_ollama import ChatOllama
    from langchain_core.tools import tool
    from langchain_core.messages import SystemMessage, HumanMessage
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    ChatOllama = None
    tool = None
    SystemMessage = None
    HumanMessage = None

from ..core.types import ActionType, AgentProposal, DailySensorSnapshot, TrustAssessment
from ..mcp_server import SpirulinaMCP

class ActionSchema(BaseModel):
    """Execute an action on the Spirulina Bioreactor."""
    action: ActionType = Field(..., description="The action to execute (HOLD, ALERT, REQUEST_VERIFICATION, ACT_SAFE, ACT_RESTRICTED).")
    rationale: str = Field(..., description="One sentence rationale for the action.")

class LlmAgent:
    def __init__(self):
        self.backend = os.getenv("LLM_BACKEND", "mock").lower()
        self.ollama_model = "llama3.1:8b" # Explicitly use installed model tag
        self.llm = None
        
        if self.backend == "ollama":
            if not HAS_LANGCHAIN:
                print("Warning: langchain-ollama not found. Falling back to MOCK.")
                self.backend = "mock"
            else:
                self.llm = ChatOllama(
                    model=self.ollama_model, 
                    temperature=0.0
                )
                print(f"Agent initialized with LangChain ChatOllama: {self.ollama_model}")
        else:
             print(f"Agent initialized in MOCK mode.")

    def proposed_action(self, mcp: SpirulinaMCP) -> AgentProposal:
        """
        Main capability: 
        1. Reads state from MCP.
        2. Uses LangChain to decide action.
        3. Parses Tool Call.
        4. Executes on MCP (Middleware Check).
        5. Returns Result.
        """
        if self.backend != "ollama":
            return self._mock_proposal(mcp)

        # 1. Gather Context from MCP
        # Note: We rely on MCP's current state being updated
        snapshot_uri = f"sensors://{mcp.current_snapshot.day}/readings"
        trust_uri = f"trust://{mcp.current_snapshot.day}/score"
        
        sensor_json = mcp.read_resource(snapshot_uri)
        trust_json = mcp.read_resource(trust_uri)
        
        # 2. Define & Bind Tool
        # We bind the MCP's execution logic as a tool for the LLM
        @tool("execute_action", args_schema=ActionSchema)
        def execute_tool(action: ActionType, rationale: str):
            """Call this to execute an action on the plant."""
            pass # We don't run it here inside LangChain, we just want the args back.
            
        llm_with_tools = self.llm.bind_tools([execute_tool])

        # 3. Prompting
        # Forced JSON/Tool-calling prompt structure for Ollama/Llama 3
        # Llama 3.1 supports tools, but sometimes needs a nudge to "Use the tool"
        sys_msg = SystemMessage(content="""You are an automated control agent for a Spirulina bioreactor.
Your goal is to maintain optimal growth while strictly adhering to trust-based safety protocols.

IMPORTANT: You DO NOT have the ability to act directly.
To perform ANY action, you MUST use the provided tool `execute_action`.
Do not output plain text. Call the tool with your decision.

Available Actions: HOLD, ALERT, REQUEST_VERIFICATION, ACT_SAFE, ACT_RESTRICTED.
Rationale: Provide a short, one-sentence rationale.

DECISION PROCESS (Follow strict order, top to bottom):

1. CHECK TRUST & DATA QUALITY:
   - Is Trust Score <= 0.4? OR Is `stale_data` present?
   - CONCEPT: If yes, you are "BLIND". Sensor flags like `drift` or `range` might be errors.
   - ACTION: STOP. COMMAND `REQUEST_VERIFICATION`. (Do NOT Alert/Hold).

2. CHECK CRITICAL ANOMALIES:
   - Is `range_violation` OR `timestamp_anomaly` present?
   - YES -> STOP. COMMAND `ALERT`.

3. CHECK WARNINGS:
   - Is `drift_suspected` OR `inconsistent_signals` present?
   - YES -> STOP. COMMAND `HOLD`.

4. NOMINAL STATE:
   - If you reached this step, NO flags are present.
   - COMMAND `ACT_RESTRICTED` (Rationale: "Optimizing yield in nominal conditions.").
""")

        human_msg = HumanMessage(content=f"""CURRENT STATE:
Sensors: {sensor_json}
Trust Status: {trust_json}

Decide the best action.
""")

        # 4. Invoke LLM
        try:
            print(f"  > calling model {self.ollama_model}...", end="", flush=True)
            ai_msg = llm_with_tools.invoke([sys_msg, human_msg])
            print(" done.")
            
            # DEBUG: Print what we got
            print(f"\n[DEBUG RAW CONTENT]: {ai_msg.content}")
            print(f"[DEBUG TOOL CALLS]: {ai_msg.tool_calls}")
            
            # 5. Extract Decision
            if ai_msg.tool_calls:
                call = ai_msg.tool_calls[0]
                args = call["args"]
                
                # Parse Args (LangChain usually handles this, but we double check)
                try:
                    action_enum = ActionType(args.get("action"))
                except ValueError:
                    # Fallback if model hallucinated a string not in Enum
                    return AgentProposal(action=ActionType.HOLD, rationale="Invalid Action Token", parse_error=True, raw_output=str(args))
                
                rationale_str = args.get("rationale", "No rationale provided.")
                
                # 6. Execute (Trust Gate)
                # We interpret the tool call by actually running it against the MCP
                result = mcp.execute_action(action_enum, rationale_str)
                
                return AgentProposal(
                    action=action_enum,
                    rationale=rationale_str,
                    raw_output=str(result), # Log the Gate result (Blocked/Success)
                    parse_error=False
                )
            else:
                # LLM didn't call tool (Chatter)
                return AgentProposal(
                    action=ActionType.HOLD, 
                    rationale="Agent failed to call tool.", 
                    parse_error=True, 
                    raw_output=ai_msg.content
                )
                
        except Exception as e:
            print(f"\n[CRITICAL ERROR in Invoke]: {e}")
            import traceback
            traceback.print_exc()
            return AgentProposal(action=ActionType.HOLD, rationale=f"LangChain Error: {e}", parse_error=True, raw_output=str(e))

    def _mock_proposal(self, mcp: SpirulinaMCP) -> AgentProposal:
        """Optimistic mock agent using MCP state."""
        trust = mcp.current_trust
        
        # 1. Decide Intent (Optimistic)
        intent = ActionType.ACT_SAFE
        rationale = "Safety mode (Mock)."
        
        # Priority 1: System Anomalies -> Verify
        if (trust.flags.get("stale_data") or 
            trust.flags.get("timestamp_anomaly") or 
            trust.flags.get("inconsistent_signals")):
            intent = ActionType.REQUEST_VERIFICATION
            rationale = "System anomaly detected (Mock)."
            
        # Priority 2: Range Violation -> Alert
        elif trust.flags.get("range_violation"):
            intent = ActionType.ALERT
            rationale = "Critical violation (Mock)."
            
        # Priority 3: Drift -> Hold
        elif trust.flags.get("drift_suspected"):
            intent = ActionType.HOLD
            rationale = "Drift suspected (Mock)."
            
        # Priority 4: High Trust -> Optimize
        elif trust.trust_score >= 0.8:
             intent = ActionType.ACT_RESTRICTED
             rationale = "Optimizing (Mock)."
             
        # 2. Execute via MCP Gate
        result = mcp.execute_action(intent, rationale)
        
        return AgentProposal(
            action=intent,
            rationale=rationale,
            raw_output=str(result),
            parse_error=False
        )
