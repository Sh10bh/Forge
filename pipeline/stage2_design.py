import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import call_llm_json

SYSTEM_PROMPT = """You are a software architect who designs clean, RESTful application systems.
You always respond with valid JSON only — no explanation, no markdown, no extra text."""

USER_PROMPT_TEMPLATE = """Design the system architecture for this app intent:

{intent_json}

Return a JSON object with exactly these fields:
{{
  "entities": [
    {{
      "name": "EntityName",
      "fields": ["field1", "field2"],
      "relationships": ["belongs_to:OtherEntity", "has_many:AnotherEntity"],
      "key_fields": ["the", "most", "important", "fields"]
    }}
  ],
  "user_flows": [
    {{
      "name": "flow_name",
      "steps": ["step 1", "step 2"],
      "roles_involved": ["role1"]
    }}
  ],
  "api_structure": [
    {{
      "resource": "resource_name",
      "endpoints": ["GET /resource", "POST /resource", "PUT /resource/:id", "DELETE /resource/:id"],
      "auth_required": true,
      "roles_allowed": ["admin", "user"]
    }}
  ],
  "permission_matrix": {{
    "admin": ["can do everything"],
    "user": ["specific permissions"]
  }}
}}

Rules:
- Every entity from the intent must appear here
- API endpoints must use RESTful conventions
- Every role from the intent must appear in permission_matrix
- Relationships use format "has_many:EntityName" or "belongs_to:EntityName"

Return ONLY valid JSON."""


def design_system(intent: dict) -> dict:
    """
    Takes the intent from stage 1 and figures out how the app should actually be structured.
    This is the blueprint everything else is generated from.
    """
    user_msg = USER_PROMPT_TEMPLATE.format(intent_json=json.dumps(intent, indent=2))
    result = call_llm_json(SYSTEM_PROMPT, user_msg)

    required_keys = ["entities", "user_flows", "api_structure", "permission_matrix"]
    missing = [k for k in required_keys if k not in result]

    if missing:
        raise ValueError(f"Stage 2 output missing keys: {missing}")

    if not isinstance(result["entities"], list) or len(result["entities"]) == 0:
        raise ValueError("Stage 2: entities must be a non-empty list")

    return result


if __name__ == "__main__":
    sample_intent = {
        "app_name": "SalesCRM",
        "app_type": "crm",
        "entities": ["User", "Contact", "Deal"],
        "features": ["login", "contacts", "dashboard", "role_based_access"],
        "roles": ["admin", "sales_rep"],
        "premium_features": [],
        "integrations": [],
        "assumptions": ["Admins have full access"]
    }
    output = design_system(sample_intent)
    print(json.dumps(output, indent=2))