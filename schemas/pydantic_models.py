# schemas/pydantic_models.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# ── DB SCHEMA ──────────────────────────────────────────────────────
class DBColumn(BaseModel):
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None

class DBTable(BaseModel):
    table_name: str
    columns: List[DBColumn]

# ── API SCHEMA ─────────────────────────────────────────────────────
class APIEndpoint(BaseModel):
    path: str
    method: str
    description: str
    request_body: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    auth_required: bool = True
    roles_allowed: List[str] = []

# ── UI SCHEMA ──────────────────────────────────────────────────────
class UIComponent(BaseModel):
    component_type: str
    fields: List[str] = []
    api_endpoint: Optional[str] = None

class UIPage(BaseModel):
    page_name: str
    route: str
    protected: bool = True
    roles_allowed: List[str] = []
    components: List[UIComponent]

# ── AUTH SCHEMA ────────────────────────────────────────────────────
class AuthRule(BaseModel):
    role: str
    permissions: List[str]

class AuthSchema(BaseModel):
    strategy: str = "JWT"
    token_expiry: str = "24h"
    roles: List[AuthRule]

# ── FULL OUTPUT (combines all 4 layers) ───────────────────────────
class AppSchema(BaseModel):
    app_name: str
    ui_schema: List[UIPage]
    api_schema: List[APIEndpoint]
    db_schema: List[DBTable]
    auth: AuthSchema
    assumptions: List[str] = []