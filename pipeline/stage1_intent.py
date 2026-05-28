import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import call_llm_json

SYSTEM_PROMPT = """You are an expert at analyzing app ideas and extracting structured intent.
You always respond with valid JSON only — no explanation, no markdown, no extra text."""

USER_PROMPT_TEMPLATE = """Analyze this app idea and extract structured intent:

"{user_prompt}"

Return a JSON object with exactly these fields:
{{
  "app_name": "short name for the app",
  "app_type": "one of: crm, ecommerce, dashboard, social, productivity, marketplace, other",
  "entities": ["list", "of", "main", "data", "objects"],
  "features": ["list", "of", "features", "mentioned"],
  "roles": ["list", "of", "user", "roles"],
  "premium_features": ["features", "behind", "paywall", "if", "any"],
  "integrations": ["third", "party", "services", "mentioned"],
  "assumptions": ["list", "of", "reasonable", "assumptions", "you", "made"]
}}

Rules:
- If something is not mentioned, infer it reasonably (e.g. most apps need a User entity)
- Always include at least one role (default: "user")
- Keep entity names singular and PascalCase
- Keep feature names short and lowercase with underscores
- Document assumptions clearly

Return ONLY valid JSON, no explanation."""


def extract_intent(user_prompt: str) -> dict:
    """
    Stage 1: Parse the user raw prompt into structured intent.
    This gives downstream stages clean data to work with.
    """
    user_msg = USER_PROMPT_TEMPLATE.format(user_prompt=user_prompt)
    result = call_llm_json(SYSTEM_PROMPT, user_msg)

    required_keys = ["app_name", "app_type", "entities", "features", "roles"]
    missing = [k for k in required_keys if k not in result]

    if missing:
        raise ValueError(f"Stage 1 output missing keys: {missing}")

    list_fields = ["entities", "features", "roles", "premium_features", "integrations", "assumptions"]
    for field in list_fields:
        if field not in result:
            result[field] = []
        elif not isinstance(result[field], list):
            result[field] = [result[field]]

    return result


if __name__ == "__main__":
    test_prompt = "Build a CRM with login, contacts management, and role-based access for admins and sales reps"
    output = extract_intent(test_prompt)
    import json
    print(json.dumps(output, indent=2))