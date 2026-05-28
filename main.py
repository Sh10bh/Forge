import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pipeline.orchestrator import run_pipeline
from utils.code_generator import generate_fastapi_stubs, generate_sql_schema

app = FastAPI(
    title="App Compiler API",
    description="Converts natural language app descriptions into structured JSON configs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str


@app.get("/")
def root():
    return {
        "message": "App Compiler is running",
        "endpoints": ["/generate", "/generate-with-stubs", "/docs"]
    }


@app.post("/generate")
async def generate(req: GenerateRequest):
    """
    Core endpoint: takes a natural language prompt, runs the 4-stage pipeline,
    returns the structured JSON config + pipeline metadata.
    """
    if not req.prompt or len(req.prompt.strip()) < 5:
        raise HTTPException(status_code=400, detail="Prompt is too short")
    
    try:
        result = run_pipeline(req.prompt)
        return {
            "success": True,
            "schema": result["schema"],
            "metadata": result["metadata"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-with-stubs")
async def generate_with_stubs(req: GenerateRequest):
    """
    Same as /generate but also produces runnable code stubs:
    - A FastAPI routes file
    - SQL CREATE TABLE statements
    
    This proves the output config is actually executable.
    """
    if not req.prompt or len(req.prompt.strip()) < 5:
        raise HTTPException(status_code=400, detail="Prompt is too short")
    
    try:
        result = run_pipeline(req.prompt)
        schema = result["schema"]
        
        # generate code stubs from the schema
        app_name = schema.get("_intent", {}).get("app_name", "MyApp")
        
        fastapi_code = ""
        sql_code = ""
        
        if "api_schema" in schema:
            fastapi_code = generate_fastapi_stubs(schema["api_schema"], app_name)
        
        if "db_schema" in schema:
            sql_code = generate_sql_schema(schema["db_schema"])
        
        return {
            "success": True,
            "schema": schema,
            "metadata": result["metadata"],
            "code_stubs": {
                "fastapi_routes": fastapi_code,
                "sql_schema": sql_code
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)