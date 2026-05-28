import sys
import os
import time
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.stage1_intent import extract_intent
from pipeline.stage2_design import design_system
from pipeline.stage3_schemas import generate_all_schemas
from pipeline.stage4_repair import run_repair_engine

# ties all 4 stages together and tracks timing/metadata


def run_pipeline(user_prompt: str) -> dict:
    """
    Full pipeline: natural language -> structured JSON config
    
    Returns both the final schema and metadata (timings, repair log, etc.)
    """
    
    if not user_prompt or len(user_prompt.strip()) < 5:
        raise ValueError("Prompt is too short or empty")
    
    metadata = {
        "prompt": user_prompt,
        "timings": {},
        "stages_completed": [],
        "repair_log": [],
        "total_time": 0
    }
    
    pipeline_start = time.time()
    
    # ── Stage 1: Intent Extraction ─────────────────────────────────────────
    print("[Stage 1] Extracting intent...")
    t = time.time()
    
    try:
        intent = extract_intent(user_prompt)
        metadata["timings"]["stage1_intent"] = round(time.time() - t, 2)
        metadata["stages_completed"].append("stage1_intent")
        print(f"  Done in {metadata['timings']['stage1_intent']}s")
    except Exception as e:
        raise RuntimeError(f"Stage 1 failed: {str(e)}")
    
    # ── Stage 2: System Design ─────────────────────────────────────────────
    print("[Stage 2] Designing system architecture...")
    t = time.time()
    
    try:
        design = design_system(intent)
        metadata["timings"]["stage2_design"] = round(time.time() - t, 2)
        metadata["stages_completed"].append("stage2_design")
        print(f"  Done in {metadata['timings']['stage2_design']}s")
    except Exception as e:
        raise RuntimeError(f"Stage 2 failed: {str(e)}")
    
    # ── Stage 3: Schema Generation ─────────────────────────────────────────
    print("[Stage 3] Generating all 4 schemas...")
    t = time.time()
    
    try:
        raw_schemas = generate_all_schemas(design)
        raw_schemas["app_name"] = intent.get("app_name","My App")
        raw_schemas["assumptions"] = intent.get("assumptions",[])
        if "auth_schema" in raw_schemas:
            raw_schemas["auth"] = raw_schemas.pop("auth_schema")
        metadata["timings"]["stage3_schemas"] = round(time.time() - t, 2)
        metadata["stages_completed"].append("stage3_schemas")
        print(f"  Done in {metadata['timings']['stage3_schemas']}s")
    except Exception as e:
        raise RuntimeError(f"Stage 3 failed: {str(e)}")
    
    # ── Stage 4: Repair Engine ─────────────────────────────────────────────
    print("[Stage 4] Running repair engine...")
    t = time.time()
    
    try:
        final_schemas, repair_log = run_repair_engine(raw_schemas)
        metadata["timings"]["stage4_repair"] = round(time.time() - t, 2)
        metadata["stages_completed"].append("stage4_repair")
        metadata["repair_log"] = repair_log
        print(f"  Done in {metadata['timings']['stage4_repair']}s")
    except Exception as e:
        # repair failed, return whatever we had before repair
        print(f"  Warning: Repair engine failed ({e}), using unrepaired output")
        final_schemas = raw_schemas
        metadata["repair_log"] = [{"status": "repair_failed", "error": str(e)}]
        metadata["stages_completed"].append("stage4_repair")
    
    # ── Final Output ───────────────────────────────────────────────────────
    metadata["total_time"] = round(time.time() - pipeline_start, 2)
    
    # attach intent and design to output for context
    final_schemas["_intent"] = intent
    final_schemas["_design"] = design
    
    print(f"\nPipeline complete in {metadata['total_time']}s")
    
    return {
        "schema": final_schemas,
        "metadata": metadata
    }


if __name__ == "__main__":
    prompt = "Build a simple task manager with login, task creation, and admin dashboard"
    result = run_pipeline(prompt)
    
    print("\n--- METADATA ---")
    print(json.dumps(result["metadata"], indent=2))
    
    print("\n--- SCHEMA KEYS ---")
    print(list(result["schema"].keys()))