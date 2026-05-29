import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import call_llm_json
from utils.validators import validate_schema, check_cross_layer_consistency

MAX_REPAIR_ATTEMPTS = 3

REPAIR_SYSTEM_PROMPT = """You are a JSON repair specialist. You fix broken or incomplete JSON schemas.
You always respond with valid JSON only — no explanation, no markdown, no extra text."""

JSON_REPAIR_USER = """Fix this broken JSON and return only the corrected version.

Broken JSON:
{broken_json}

Error:
{error}

Return the corrected valid JSON only."""

FIELD_REPAIR_USER = """This JSON is missing required fields or has wrong types. Fix only the listed issues.

Current JSON:
{current_json}

Validation errors:
{errors}

Keep everything else exactly the same. Return the corrected JSON only."""

CONSISTENCY_REPAIR_USER = """Fix cross-layer inconsistencies in this app schema.

Full Schema:
{full_schema}

Inconsistencies:
{inconsistencies}

Rules:
- DB schema is the source of truth for field names
- API endpoints must use fields that exist in DB tables
- UI components must point to real API endpoints
- Only change what is listed as inconsistent

Return the complete fixed schema as JSON."""


def try_parse_json(raw_text: str):
    try:
        return json.loads(raw_text), None
    except json.JSONDecodeError as e:
        return None, str(e)


def repair_json(broken_text: str, error: str) -> dict:
    user_msg = JSON_REPAIR_USER.format(broken_json=broken_text[:3000], error=error)
    return call_llm_json(REPAIR_SYSTEM_PROMPT, user_msg)


def repair_missing_fields(schema: dict, errors: list) -> dict:
    user_msg = FIELD_REPAIR_USER.format(
        current_json=json.dumps(schema, indent=2),
        errors="\n".join(errors)
    )
    return call_llm_json(REPAIR_SYSTEM_PROMPT, user_msg)


def repair_consistency(full_schema: dict, inconsistencies: list) -> dict:
    user_msg = CONSISTENCY_REPAIR_USER.format(
        full_schema=json.dumps(full_schema, indent=2),
        inconsistencies="\n".join(inconsistencies)
    )
    return call_llm_json(REPAIR_SYSTEM_PROMPT, user_msg)


def run_repair_engine(raw_schemas: dict) -> tuple:
    """
    Core repair loop. Up to MAX_REPAIR_ATTEMPTS passes.
    Each attempt detects what is wrong and fixes only that part.
    Returns (repaired_schema, repair_log).
    """
    repair_log = []
    current = raw_schemas.copy()

    for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
        print(f"  Repair attempt {attempt}/{MAX_REPAIR_ATTEMPTS}")
        issues_found = []

        # Check 1: valid JSON on any string layers
        for layer_name in ["db_schema", "api_schema", "ui_schema", "auth_schema"]:
            layer = current.get(layer_name)
            if isinstance(layer, str):
                parsed, err = try_parse_json(layer)
                if err:
                    print(f"    Fixing malformed JSON in {layer_name}")
                    current[layer_name] = repair_json(layer, err)
                    repair_log.append({"attempt": attempt, "type": "invalid_json", "layer": layer_name, "error": err})
                    issues_found.append(f"json_error:{layer_name}")
                else:
                    current[layer_name] = parsed

        # Check 2: Pydantic validation
        pydantic_errors = validate_schema(current)
        if pydantic_errors:
            print(f"    Fixing Pydantic errors...")
            broken_layer = None
            for err in pydantic_errors:
                for layer in ["db_schema", "api_schema", "ui_schema", "auth_schema"]:
                    if layer in err.lower():
                        broken_layer = layer
                        break
            if broken_layer:
                try:
                    current[broken_layer] = repair_missing_fields(current[broken_layer], pydantic_errors)
                except Exception as repair_err:
                    print(f" Could not repair {broken_layer}: {repair_err}, skipping")
            else:
                try:
                    current = repair_missing_fields(current, pydantic_errors)
                except Exception as repair_err:
                    print(f" Could not repair schema: {repair_err}, skipping")
            repair_log.append({"attempt": attempt, "type": "pydantic_validation", "errors": pydantic_errors})
            issues_found.append("pydantic_errors")

        # Check 3: Cross-layer consistency
        consistency_issues = check_cross_layer_consistency(current)
        if consistency_issues:
            print(f"    Fixing {len(consistency_issues)} consistency issue(s)...")
            fixed = repair_consistency(current, consistency_issues)
            for layer in ["db_schema", "api_schema", "ui_schema", "auth_schema"]:
                if layer in fixed:
                    current[layer] = fixed[layer]
            repair_log.append({"attempt": attempt, "type": "cross_layer_consistency", "issues": consistency_issues})
            issues_found.append("consistency_issues")

        if not issues_found:
            print(f"    All checks passed on attempt {attempt}")
            break

    if not repair_log:
        repair_log.append({"status": "no_repairs_needed"})
    else:
        repair_log.append({"status": "completed", "total_repairs": len([r for r in repair_log if "type" in r])})

    return current, repair_log


if __name__ == "__main__":
    # test with a clean schema — should need no repairs
    clean_schema = {
        "db_schema": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "uuid", "primary_key": True, "required": True, "unique": True, "foreign_key": None},
                        {"name": "email", "type": "string", "required": True, "unique": True, "primary_key": False, "foreign_key": None},
                        {"name": "created_at", "type": "datetime", "required": True, "unique": False, "primary_key": False, "foreign_key": None},
                        {"name": "updated_at", "type": "datetime", "required": True, "unique": False, "primary_key": False, "foreign_key": None}
                    ],
                    "indexes": ["email"]
                }
            ],
        "api_schema": [
                {
                    "path": "/api/auth/login",
                    "method": "POST",
                    "description": "User login",
                    "auth_required": False,
                    "roles_allowed": [],
                    "request_body": {"email": "string", "password": "string"},
                    "response_schema": {"token": "string"},
                    "db_tables_used": ["users"]
                }
            ],
        "ui_schema": [
                {
                    "name": "Login",
                    "route": "/login",
                    "auth_required": False,
                    "roles_allowed": [],
                    "components": [
                        {
                            "type": "form",
                            "name": "LoginForm",
                            "api_endpoint": "/api/auth/login",
                            "api_method": "POST",
                            "fields": ["email", "password"]
                        }
                    ]
                }
            ],
        "auth_schema": {
            "auth_type": "jwt",
            "token_expiry": "24h",
            "roles": [
                {
                    "name": "user",
                    "description": "Regular user",
                    "permissions": [{"resource": "users", "actions": ["read"]}]
                }
            ],
            "rules": []
        }
    }

    repaired, log = run_repair_engine(clean_schema)
    print("Repair log:", json.dumps(log, indent=2))