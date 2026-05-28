import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.orchestrator import run_pipeline

# runs all test prompts and tracks: success rate, latency, retries, failure types
# outputs a proper evaluation_results.json with summary stats


def load_test_prompts() -> list:
    prompts_path = os.path.join(os.path.dirname(__file__), "test_prompts.json")
    with open(prompts_path) as f:
        data = json.load(f)
    
    all_prompts = []
    
    for p in data["normal_prompts"]:
        all_prompts.append({
            "id": p["id"],
            "type": "normal",
            "prompt": p["prompt"]
        })
    
    for p in data["edge_case_prompts"]:
        all_prompts.append({
            "id": p["id"],
            "type": f"edge_{p['type']}",
            "prompt": p["prompt"],
            "expected_behavior": p.get("expected_behavior"),
            "notes": p.get("notes")
        })
    
    return all_prompts


def count_repairs(repair_log: list) -> int:
    return len([r for r in repair_log if "type" in r])


def classify_failure(error_msg: str) -> str:
    err = error_msg.lower()
    if "json" in err:
        return "invalid_json"
    elif "stage 1" in err:
        return "intent_extraction_failed"
    elif "stage 2" in err:
        return "system_design_failed"
    elif "stage 3" in err:
        return "schema_generation_failed"
    elif "stage 4" in err:
        return "repair_engine_failed"
    elif "timeout" in err or "rate" in err:
        return "api_error"
    else:
        return "unknown_error"


def run_evaluation(delay_between: float = 1.5) -> dict:
    """
    Runs all 20 prompts through the pipeline and collects metrics.
    
    delay_between: seconds to wait between requests (Groq has rate limits)
    """
    
    prompts = load_test_prompts()
    results = []
    
    print(f"\nRunning evaluation on {len(prompts)} prompts...\n")
    print("=" * 60)
    
    for i, test in enumerate(prompts):
        print(f"\n[{i+1}/{len(prompts)}] ID: {test['id']} | Type: {test['type']}")
        print(f"Prompt: {test['prompt'][:80]}{'...' if len(test['prompt']) > 80 else ''}")
        
        start = time.time()
        success = False
        error_msg = None
        schema_keys = []
        repair_count = 0
        stages_completed = []
        
        try:
            result = run_pipeline(test["prompt"])
            
            success = True
            schema = result.get("output") or result.get("schema",{})
            schema_keys = [k for k in schema.keys() if not k.startswith("_")]
            repair_count = count_repairs(result["metadata"].get("repair_log", []))
            stages_completed = result["metadata"].get("stages_completed", [])
            
            print(f"  ✓ Success | Schemas: {schema_keys} | Repairs: {repair_count}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"  ✗ Failed: {error_msg[:100]}")
        
        latency = round(time.time() - start, 2)
        
        results.append({
            "id": test["id"],
            "type": test["type"],
            "prompt": test["prompt"],
            "success": success,
            "latency_seconds": latency,
            "stages_completed": stages_completed,
            "schema_layers_generated": schema_keys,
            "repair_count": repair_count,
            "error": error_msg,
            "failure_type": classify_failure(error_msg) if error_msg else None
        })
        
        # respect Groq rate limits
        if i < len(prompts) - 1:
            time.sleep(delay_between)
    
    # ── Summary Stats ──────────────────────────────────────────────────────
    total = len(results)
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    normal_results = [r for r in results if r["type"] == "normal"]
    edge_results = [r for r in results if r["type"].startswith("edge")]
    
    avg_latency = round(sum(r["latency_seconds"] for r in successful) / len(successful), 2) if successful else 0
    avg_repairs = round(sum(r["repair_count"] for r in successful) / len(successful), 2) if successful else 0
    
    # failure type breakdown
    failure_types = {}
    for r in failed:
        ft = r.get("failure_type", "unknown")
        failure_types[ft] = failure_types.get(ft, 0) + 1
    
    summary = {
        "total_prompts": total,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": f"{round(len(successful)/total*100, 1)}%",
        "normal_prompts": {
            "total": len(normal_results),
            "success_rate": f"{round(sum(1 for r in normal_results if r['success'])/len(normal_results)*100, 1)}%" if normal_results else "N/A"
        },
        "edge_case_prompts": {
            "total": len(edge_results),
            "success_rate": f"{round(sum(1 for r in edge_results if r['success'])/len(edge_results)*100, 1)}%" if edge_results else "N/A"
        },
        "avg_latency_seconds": avg_latency,
        "avg_repairs_per_request": avg_repairs,
        "failure_type_breakdown": failure_types
    }
    
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print(f"Success rate: {summary['success_rate']} ({len(successful)}/{total})")
    print(f"Avg latency: {avg_latency}s")
    print(f"Avg repairs: {avg_repairs}")
    if failure_types:
        print(f"Failure types: {failure_types}")
    
    output = {
        "summary": summary,
        "results": results
    }
    
    # save to file
    output_path = os.path.join(os.path.dirname(__file__), "evaluation_results.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to {output_path}")
    return output


if __name__ == "__main__":
    run_evaluation()