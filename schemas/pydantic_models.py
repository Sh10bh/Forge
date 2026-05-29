# schemas/pydantic_models.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# ── DB SCHEMA ──────────────────────────────────────────────────────
class DBColumn(BaseModel):
    name: str
    type: str
    required: bool = True
    unique: bool = False
    primary_key: bool = False
    foreign_key: Optional[str] = None

class DBTable(BaseModel):
    name: str
    columns: List[DBColumn]
    indexes: List[str] = []

# ── API SCHEMA ─────────────────────────────────────────────────────
class APIEndpoint(BaseModel):
    path: str
    method: str
    description: str
    request_body: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    auth_required: bool = True
    roles_allowed: List[str] = []
    db_tables_used: List[str] = []

# ── UI SCHEMA ──────────────────────────────────────────────────────
class UIComponent(BaseModel):
    type: str
    name: str = ""
    fields: List[str] = []
    api_endpoint: Optional[str] = None
    api_method: Optional[str] = None

class UIPage(BaseModel):
    name: str
    route: str
    auth_required: bool = True
    roles_allowed: List[str] = []
    components: List[UIComponent]

class UISchema(BaseModel):
    pages: List[UIPage]
    navigation: List[Dict[str, Any]] = []

# ── AUTH SCHEMA ────────────────────────────────────────────────────
class AuthPermission(BaseModel):
    resource: str
    actions: List[str] = []

class AuthRule(BaseModel):
    name: str
    description: str = ""
    permissions: List[AuthPermission] = []

class AuthSchema(BaseModel):
    auth_type: str = "jwt"
    token_expiry: str = "24h"
    roles: List[AuthRule]
    rules: List[Dict[str, Any]] = []

# ── FULL OUTPUT (combines all 4 layers) ────────────────────────────
class AppSchema(BaseModel):
    db_schema: Any
    api_schema: Any
    ui_schema: Any
    auth_schema: Any
    assumptions: List[str] = []