
import sys
import os

print("DEBUG: Python started.", flush=True)
print(f"DEBUG: CWD = {os.getcwd()}", flush=True)
print(f"DEBUG: Sys Path = {sys.path}", flush=True)

try:
    print("DEBUG: Importing V3.main...", flush=True)
    import V3.main
    print("DEBUG: Import successful. Running main...", flush=True)
    V3.main.main()
except Exception as e:
    print(f"DEBUG: Error happened: {e}", flush=True)
