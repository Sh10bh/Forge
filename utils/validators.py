from schemas.pydantic_models import AppSchema
from pydantic import ValidationError
from typing import Tuple, List

def validate_schema(output: dict) -> Tuple[bool, List[str]]:
    try:
        AppSchema(**output)
        return True, []
    except ValidationError as e:
        # collect exactly which fields failed and why
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return False, errors


def check_cross_layer_consistency(output: dict) -> List[str]:
    issues = []

    # grab every column name from every db table
    db_fields = set()
    for table in output.get("db_schema", []):
        for col in table.get("columns", []):
            db_fields.add(col["name"])

    # check api request body fields actually exist in db
    for endpoint in output.get("api_schema", []):
        body = endpoint.get("request_body") or {}
        for field in body:
            if field not in db_fields and field not in ["password", "token"]:
                issues.append(
                    f"API {endpoint['path']} uses field '{field}' "
                    f"but it doesn't exist in any DB table"
                )

    # check ui components point to real api endpoints
    api_paths = {e["path"] for e in output.get("api_schema", [])}
    for page in output.get("ui_schema", []):
        for comp in page.get("components", []):
            ep = comp.get("api_endpoint")
            if ep and ep not in api_paths:
                issues.append(
                    f"UI page '{page['route']}' references "
                    f"non-existent API endpoint: {ep}"
                )

    return issues