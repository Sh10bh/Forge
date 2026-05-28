# Forge

> Natural language → validated, executable JSON config in 4 pipeline stages.

**[Live Demo](https://your-render-url.up.render.app)** · **[Video Walkthrough](#)** 

---

![Forge Screenshot](frontend/screenshot.png)

---

## The Problem

LLMs are bad at producing structured output reliably. A single prompt asking for "a full app schema" will hallucinate fields, produce inconsistent JSON, and fail silently. This project treats app generation like a **compiler** — breaking the process into discrete, verifiable stages where each stage's output is validated before the next stage runs.

---

## Pipeline Architecture

```
User Prompt
    │
    ▼
┌─────────────────────────────────┐
│  Stage 1 — Intent Extraction    │  "Build a CRM with login..."
│  Parses raw prompt into         │  →  app_name, entities, roles,
│  structured intent object       │     features, assumptions
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Stage 2 — System Design        │  Intent
│  Converts intent into           │  →  entities + relationships,
│  concrete app architecture      │     api_structure, permission_matrix
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Stage 3 — Schema Generation    │  4 chained LLM calls:
│  Each call feeds into the next  │  DB → API → UI → Auth
│  to enforce cross-layer         │  (API fields pulled from DB columns,
│  consistency from the start     │   UI endpoints matched to API paths)
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Stage 4 — Repair Engine        │  Detects 3 error types separately:
│  Validates output, detects      │  1. Invalid / malformed JSON
│  issues, fixes only the broken  │  2. Missing Pydantic fields
│  layer (not blind full retry)   │  3. Cross-layer inconsistencies
│  Up to 3 targeted repair passes │  Fixes the specific layer, not all
└─────────────────────────────────┘
               │
               ▼
    Validated JSON Config
    + FastAPI route stubs
    + SQL CREATE TABLE statements
```

**Why multi-stage?** A single prompt producing a full app schema has no checkpoints — if the DB schema hallucinates a field name, the API and UI schemas silently inherit the error. Staging lets each layer validate before the next builds on top of it.

---

## Output Structure

Every successful run produces 4 validated layers:

```json
{
  "db_schema": {
    "tables": [{ "name": "users", "columns": [...] }]
  },
  "api_schema": {
    "endpoints": [{ "path": "/api/auth/login", "method": "POST", ... }]
  },
  "ui_schema": {
    "pages": [{ "name": "Login", "route": "/login", "components": [...] }]
  },
  "auth_schema": {
    "auth_type": "jwt",
    "roles": [{ "name": "admin", "permissions": [...] }]
  }
}
```

Cross-layer rules enforced automatically:
- API `request_body` fields must match DB column names
- UI component `api_endpoint` values must match real API paths
- Every role in `permission_matrix` must appear in `auth_schema`

---

## Repair Engine (Core Feature)

The repair engine is what separates this from a wrapper. It runs up to **3 targeted passes** after schema generation:

| Error Type | Detection | Fix Strategy |
|---|---|---|
| Invalid JSON | `json.JSONDecodeError` | LLM rewrites only the broken layer |
| Missing fields | Pydantic v2 `ValidationError` | Identifies which layer failed, repairs that layer only |
| Cross-layer mismatch | Custom consistency checker | Sends full schema + inconsistency list, LLM fixes references |

It does **not** re-run the entire pipeline on failure. If only the UI schema has a bad endpoint reference, only the UI schema gets repaired.

---

## Evaluation Results

Ran 20 prompts through the full pipeline — 10 normal product prompts and 10 edge cases (vague, conflicting, incomplete, gibberish).

| Metric | Result |
|---|---|
| Overall success rate | tracked in `evaluation_results.json` |
| Normal prompts success rate | tracked in `evaluation_results.json` |
| Edge case success rate | tracked in `evaluation_results.json` |
| Avg latency per request | tracked in `evaluation_results.json` |
| Avg repairs per request | tracked in `evaluation_results.json` |

Run the evaluation yourself:

```bash
python evaluation/run_eval.py
# outputs evaluation/evaluation_results.json
```

Edge cases tested include: single-word prompts, contradictory permissions, no-auth apps, mixed-language input, extremely large scope, and near-gibberish input.

---

## Project Structure

```
app_compiler/
├── pipeline/
│   ├── stage1_intent.py      # LLM call → structured intent object
│   ├── stage2_design.py      # LLM call → architecture + permission matrix
│   ├── stage3_schemas.py     # 4 chained LLM calls → DB, API, UI, Auth
│   ├── stage4_repair.py      # validation + targeted repair engine
│   └── orchestrator.py       # connects all stages, tracks timing
├── schemas/
│   └── pydantic_models.py    # type contracts for all 4 schema layers
├── utils/
│   ├── llm_client.py         # Groq API wrapper (call_llm, call_llm_json)
│   ├── validators.py         # Pydantic + cross-layer consistency checks
│   └── code_generator.py     # FastAPI stub + SQL generator from schemas
├── evaluation/
│   ├── test_prompts.json     # 10 normal + 10 edge case prompts
│   ├── run_eval.py           # evaluation runner with metric tracking
│   └── evaluation_results.json
├── frontend/
│   └── index.html            # single-file UI, no build step
├── main.py                   # FastAPI server
├── requirements.txt
└── .env                      # GROQ_API_KEY
```

---

## Running Locally

```bash
git clone https://github.com/yourusername/app-compiler
cd app_compiler

pip install -r requirements.txt

# create .env with your key
echo "GROQ_API_KEY=your_key_here" > .env

# start the server
uvicorn main:app --reload

# open the UI
open frontend/index.html
```

API is at `http://localhost:8000/docs` — fully interactive via Swagger.

---

## API Endpoints

**`POST /generate`**
```json
{ "prompt": "Build a task manager with login and admin dashboard" }
```
Returns: validated 4-layer JSON config + pipeline metadata (timings, repair log).

**`POST /generate-with-stubs`**
Same as above, additionally returns:
- `code_stubs.fastapi_routes` — runnable Python FastAPI file
- `code_stubs.sql_schema` — SQL `CREATE TABLE` statements

These stubs prove the output config is directly executable, not just abstract JSON.

---

## Stack

| Layer | Choice | Reason |
|---|---|---|
| LLM | Groq (Llama 3.3 70B) | Fast inference, free tier, reliable JSON output |
| Validation | Pydantic v2 | Strict type enforcement, clear error messages for repair targeting |
| Backend | FastAPI | Async, auto-docs, easy CORS setup |
| Frontend | Vanilla HTML/CSS/JS | Zero build step, easy to host on GitHub Pages |

---

## Deployment

Backend hosted on **Render** — set `GROQ_API_KEY` in Render environment variables, push to GitHub, Render auto-deploys via `render.toml`.

Frontend hosted on **GitHub Pages** — enable Pages on the `main` branch pointing to `/frontend`.

Update `API_BASE` in `frontend/index.html` with your Render URL before deploying the frontend.

---

*Built by Shubh Gupta — VIT Bhopal, CS 3rd year*
