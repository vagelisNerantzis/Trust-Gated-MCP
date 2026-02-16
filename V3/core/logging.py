import os
import csv
from typing import Optional
from .config import AppConfig

class ExperimentLogger:
    """
    Handles audit-proof logging for V3 experiments.
    Enforces schema with backend, model, and explicit action tracking.
    """
    def __init__(self, config: AppConfig):
        self.config = config
        self.output_dir = config.project.output_dir
        self.log_path = os.path.join(self.output_dir, "experiment_log.csv")
        self.file = None
        self.writer = None
        
        # Resolve Backend/Model from Config or Env (Audit Sourcing)
        # Priority: Env > Config > Default
        self.backend = os.environ.get("LLM_BACKEND", getattr(config.deployment, "llm_backend", "mock"))
        self.model = os.environ.get("OLLAMA_MODEL", getattr(config.deployment, "model_name", "unknown"))

    def __enter__(self):
        os.makedirs(self.output_dir, exist_ok=True)
        # Overwrite mode for new experiment run
        self.file = open(self.log_path, "w", newline="")
        self.writer = csv.writer(self.file)
        
        # Schema Definition
        self.headers = [
            "scenario_id", 
            "day", 
            "backend", 
            "model", 
            "trust_score", 
            "mode", 
            "flags", 
            "proposed_action", 
            "executed_action", 
            "model_digest",
            "status", 
            "override", 
            "action" # Deprecated, alias for executed_action
        ]
        self.writer.writerow(self.headers)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()

    def log_result(self, 
                   scenario_id: str, 
                   day: int, 
                   trust_score: float, 
                   mode: str, 
                   flags: str, 
                   proposed_action: str, 
                   executed_action: str, 
                   status: str, 
                   override: bool,
                   model_digest: str = ""):
        """
        Log a single simulation step result.
        """
        row = [
            scenario_id,
            day,
            self.backend,
            self.model,
            f"{trust_score:.4f}", # Format score for consistency
            mode,
            flags,
            proposed_action,
            executed_action,
            model_digest,
            status,
            override,
            executed_action # Legacy action column
        ]
        if self.writer:
            self.writer.writerow(row)
            self.file.flush()
