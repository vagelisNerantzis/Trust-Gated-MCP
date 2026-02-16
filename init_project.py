import os
from pathlib import Path

def init_project():
    # Define root (relative to where this script runs)
    root = Path.cwd()
    
    # Structure definition
    dirs = [
        "experiments",
        "experiments/core",
        "experiments/scenarios",
        "experiments/trust_engine",
        "experiments/policy",
        "experiments/llm_agent",
        "experiments/logs",
        "experiments/results",
    ]
    
    files = [
        "experiments/__init__.py",
        "experiments/core/__init__.py",
        "experiments/scenarios/__init__.py",
        "experiments/trust_engine/__init__.py",
        "experiments/policy/__init__.py",
        "experiments/llm_agent/__init__.py",
        "experiments/results/__init__.py",
    ]
    
    print(f"Initializing project structure at {root}...")
    
    for d in dirs:
        path = root / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {path}")
        
    for f in files:
        path = root / f
        path.touch(exist_ok=True)
        print(f"Created file: {path}")
        
    print("Project structure check passed.")

if __name__ == "__main__":
    init_project()
