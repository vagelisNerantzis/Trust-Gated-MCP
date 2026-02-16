import sys
import os

print("Starting Dependency Check...", flush=True)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("Importing core.config...", flush=True)
from core.config import load_config
print("Importing core.types...", flush=True)
from core.types import ToolCallV1, ActionType

print("Importing mcp_host.server...", flush=True)
from mcp_host.server import SpirulinaMCP_V3

print("Importing simulation.generator...", flush=True)
from simulation.generator import SeededGenerator

print("All imports successful.", flush=True)
