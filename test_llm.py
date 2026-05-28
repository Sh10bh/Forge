from utils.llm_client import call_llm, call_llm_json

print("=== Testing call_llm ===")
r = call_llm("You are a helpful assistant.", "Say exactly: API works")
print(r)

print("\n=== Testing call_llm_json ===")
r = call_llm_json("Return only valid JSON, no explanation.", '{"status": "ok", "value": 42}')
print(r)
print("Type:", type(r))