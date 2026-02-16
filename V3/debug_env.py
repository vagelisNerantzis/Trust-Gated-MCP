import sys
import os

print(f"CWD: {os.getcwd()}")
print(f"PYTHONPATH: {sys.path}")

try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from core.config import load_config
    print("Core Config imported successfully.")
    
    cfg = load_config("c:/GitFolders/TrustGatedMCP_V2/V3/config/config.yaml")
    print(f"Config Loaded. Output Dir: {cfg.project.output_dir}")
    
    os.makedirs(cfg.project.output_dir, exist_ok=True)
    print(f"Makedirs {cfg.project.output_dir} success.")
    
    from mcp_host.server import SpirulinaMCP_V3
    print("MCP Host imported successfully.")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
