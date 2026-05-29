from schemas.pydantic_models import AppSchema
from pydantic import ValidationError
from typing import List

def validate_schema(output: dict) -> List[str]:
    """
    Returns a list of error strings.
    Empty list = valid. Non-empty list = problems found.
    """
    try:
        AppSchema(**output)
        return []
    except ValidationError as e:
        return [f"{err['loc']}: {err['msg']}" for err in e.errors()]


def check_cross_layer_consistency(output: dict) -> List[str]:
    issues = []

    # db_schema is {"tables": [...]} so grab the list first
    db_tables = output.get("db_schema", {})
    if isinstance(db_tables, dict):
        db_tables = db_tables.get("tables", [])

    # collect every column name from every db table
    db_fields = set()
    for table in db_tables:
        for col in table.get("columns", []):
            db_fields.add(col.get("name", ""))

    # api_schema is {"endpoints": [...]}
    api_endpoints = output.get("api_schema", {})
    if isinstance(api_endpoints, dict):
        api_endpoints = api_endpoints.get("endpoints", [])

    # check api request body fields exist in db
    for endpoint in api_endpoints:
        body = endpoint.get("request_body") or {}
        for field in body:
            if field not in db_fields and field not in ["password", "token", "confirm_password"]:
                issues.append(
                    f"API {endpoint.get('path', '?')} uses field '{field}' "
                    f"not found in any DB table"
                )

    # ui_schema is {"pages": [...]}
    ui_pages = output.get("ui_schema", {})
    if isinstance(ui_pages, dict):
        ui_pages = ui_pages.get("pages", [])

    # check ui components point to real api endpoints
    api_paths = {e.get("path") for e in api_endpoints}
    for page in ui_pages:
        for comp in page.get("components", []):
            ep = comp.get("api_endpoint")
            if ep and ep not in api_paths:
                issues.append(
                    f"UI page '{page.get('name', '?')}' references "
                    f"non-existent API endpoint: {ep}"
                )

    return issues