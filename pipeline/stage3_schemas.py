import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import call_llm_json

SYSTEM_PROMPT = """You are a database and API architect. You always respond with valid JSON only.
No explanation, no markdown fences, no extra text — just the JSON object."""

DB_USER_PROMPT = """Generate a database schema for this app design:

{design_json}

Return JSON with this exact structure:
{{
  "tables": [
    {{
      "name": "table_name",
      "columns": [
        {{
          "name": "column_name",
          "type": "one of: string, integer, float, boolean, datetime, text, uuid",
          "required": true,
          "unique": false,
          "primary_key": false,
          "foreign_key": null
        }}
      ],
      "indexes": ["column_name"]
    }}
  ]
}}

Rules:
- Every entity in the design gets a table
- Every table must have an "id" column (uuid, primary_key: true)
- Foreign keys format: "other_table.id"
- Use snake_case for all names
- Add created_at and updated_at (datetime, required: true) to every table

Return ONLY valid JSON."""

API_USER_PROMPT = """Generate an API schema. Field names must match the DB column names exactly.

Design:
{design_json}

Database Schema:
{db_schema_json}

Return JSON with this exact structure:
{{
  "endpoints": [
    {{
      "path": "/api/resource",
      "method": "GET",
      "description": "what this endpoint does",
      "auth_required": true,
      "roles_allowed": ["admin", "user"],
      "request_body": {{}},
      "response_schema": {{"field": "type"}},
      "db_tables_used": ["table_name"]
    }}
  ]
}}

Rules:
- Field names in request_body and response_schema MUST match DB column names
- Auth endpoints: POST /api/auth/login, POST /api/auth/register
- Use empty object for request_body on GET requests

Return ONLY valid JSON."""

UI_USER_PROMPT = """Generate a UI schema. Every api_endpoint must match a real path in the API schema.

Design:
{design_json}

API Schema:
{api_schema_json}

Return JSON with this exact structure:
{{
  "pages": [
    {{
      "name": "PageName",
      "route": "/route",
      "auth_required": true,
      "roles_allowed": ["admin"],
      "components": [
        {{
          "type": "one of: form, table, card, chart, button, input, modal, navbar",
          "name": "ComponentName",
          "api_endpoint": "/api/endpoint",
          "api_method": "GET",
          "fields": ["field1", "field2"]
        }}
      ]
    }}
  ],
  "navigation": [
    {{
      "label": "Nav Item",
      "route": "/route",
      "roles_allowed": ["admin", "user"]
    }}
  ]
}}

Rules:
- Every api_endpoint in components must match a path in the API schema
- Login and Register pages have auth_required: false
- Field names in components must match API response_schema fields

Return ONLY valid JSON."""

AUTH_USER_PROMPT = """Generate an auth and permissions schema for this app.

Design:
{design_json}

Return JSON with this exact structure:
{{
  "auth_type": "jwt",
  "token_expiry": "24h",
  "roles": [
    {{
      "name": "role_name",
      "description": "what this role can do",
      "permissions": [
        {{
          "resource": "table_or_endpoint_name",
          "actions": ["create", "read", "update", "delete"]
        }}
      ]
    }}
  ],
  "rules": [
    {{
      "rule": "description of the rule",
      "applies_to": "role_name",
      "condition": "e.g. can only access own records"
    }}
  ]
}}

Rules:
- Every role from the design must appear here
- Admin role gets full permissions on all resources
- Add a rule for each permission restriction in the design

Return ONLY valid JSON."""


def generate_db_schema(design: dict) -> dict:
    user_msg = DB_USER_PROMPT.format(design_json=json.dumps(design, indent=2))
    result = call_llm_json(SYSTEM_PROMPT, user_msg)
    if "tables" not in result or not isinstance(result["tables"], list):
        raise ValueError("DB schema missing tables list")
    return result


def generate_api_schema(design: dict, db_schema: dict) -> dict:
    user_msg = API_USER_PROMPT.format(
        design_json=json.dumps(design, indent=2),
        db_schema_json=json.dumps(db_schema, indent=2)
    )
    result = call_llm_json(SYSTEM_PROMPT, user_msg)
    if "endpoints" not in result or not isinstance(result["endpoints"], list):
        raise ValueError("API schema missing endpoints list")
    return result


def generate_ui_schema(design: dict, api_schema: dict) -> dict:
    user_msg = UI_USER_PROMPT.format(
        design_json=json.dumps(design, indent=2),
        api_schema_json=json.dumps(api_schema, indent=2)
    )
    result = call_llm_json(SYSTEM_PROMPT, user_msg)
    if "pages" not in result or not isinstance(result["pages"], list):
        raise ValueError("UI schema missing pages list")
    return result


def generate_auth_schema(design: dict) -> dict:
    user_msg = AUTH_USER_PROMPT.format(design_json=json.dumps(design, indent=2))
    result = call_llm_json(SYSTEM_PROMPT, user_msg)
    if "roles" not in result or not isinstance(result["roles"], list):
        raise ValueError("Auth schema missing roles list")
    return result


def generate_all_schemas(design: dict) -> dict:
    """
    Run all 4 schema generators in order.
    Each one gets context from the previous — this keeps them consistent.
    """
    print("  Generating DB schema...")
    db_schema = generate_db_schema(design)
    time.sleep(5)

    print("  Generating API schema...")
    api_schema = generate_api_schema(design, db_schema)
    time.sleep(5)

    print("  Generating UI schema...")
    ui_schema = generate_ui_schema(design, api_schema)
    time.sleep(5)

    print("  Generating Auth schema...")
    auth_schema = generate_auth_schema(design)

    return {
        "db_schema": db_schema["tables"],
        "api_schema": api_schema["endpoints"],
        "ui_schema": ui_schema["pages"],
        "auth_schema": auth_schema
    }


if __name__ == "__main__":
    sample_design = {
        "entities": [
            {
                "name": "User",
                "fields": ["id", "email", "password", "role"],
                "relationships": [],
                "key_fields": ["email"]
            }
        ],
        "user_flows": [
            {
                "name": "login",
                "steps": ["Enter credentials", "Receive JWT token"],
                "roles_involved": ["user", "admin"]
            }
        ],
        "api_structure": [
            {
                "resource": "auth",
                "endpoints": ["POST /api/auth/login", "POST /api/auth/register"],
                "auth_required": False,
                "roles_allowed": []
            }
        ],
        "permission_matrix": {
            "admin": ["full_access"],
            "user": ["read_own", "update_own"]
        }
    }
    output = generate_all_schemas(sample_design)
    print(json.dumps(output, indent=2))