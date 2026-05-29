from pipeline.orchestrator import run_pipeline
import json

result = run_pipeline("Build a simple todo app with login")
print(json.dumps(result["metadata"], indent=2))