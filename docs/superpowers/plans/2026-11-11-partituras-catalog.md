# Partituras Catalog App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web app for Alberto to catalog 10,000+ music scores, track where each one is stored, and query the collection via a Spanish-language chat agent.

**Architecture:** FastAPI backend with SQLite (two-level model: `piezas` + `archivos`), Jinja2 + HTMX frontend served from the same process, and a Claude API chat agent with function-calling tools that query the DB directly. The app runs on the user's Mac and is accessed from iPad/phone via WiFi.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy (ORM), SQLite, Jinja2, HTMX, Anthropic Python SDK (`anthropic`), `python-dotenv`, `pytest`, `httpx` (test client)

**Spec:** `/Users/toronjo/.claude/plans/vivid-mapping-origami.md`

## Global Constraints

- Language: all UI copy, chat responses, and log messages must be in Spanish
- Python 3.11+; no pinned minor versions for deps
- DB file: `~/Documents/Proyectos/partituras-app/partituras.db` (configurable via `.env`)
- Server binds `0.0.0.0:8000` so iPad/phone on same WiFi can connect
- Music file extensions to scan: `.pdf`, `.mxl`, `.musicxml`, `.mscz`, `.mscx`, `.sib`, `.musx`, `.capx`
- `difficulty` values: `"fácil"`, `"intermedio"`, `"avanzado"` (or `null`)
- `location_type` values: `"mac"`, `"icloud"`, `"ipad"`, `"celular"`, `"papel"`
- `format` values: `"pdf"`, `"musicxml"`, `"mscz"`, `"mscx"`, `"sib"`, `"musx"`, `"capx"`, `"papel"`, `"otro"`
- Claude model for chat agent: `claude-sonnet-4-6`
- Existing inventory to import: `~/Documents/Musica/inventario_portafolio.csv`

## Review Focus

- **Fuzzy title search with accented characters:** "Cancion" should match "Canción"; use `LOWER()` + accent-stripping in SQLite or Python-side normalization
- **Re-scan without data loss:** scanning the same folder twice must not duplicate entries or overwrite manual edits; use file path as unique key per `Archivo`
- **10,000 record list performance:** the main catalog list must paginate (50/page) and not load all records at once
- **iCloud paths:** iCloud Drive on Mac lives at `~/Library/Mobile Documents/com~apple~CloudDocs/`; `location_type` should auto-detect when a path starts with that prefix
- **Chat agent empty results:** when no pieces match a query, the agent must return a helpful Spanish message, not an empty list or error

---

## File Structure

```
partituras-app/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, mounts static/templates, registers routers
│   ├── config.py        # Settings loaded from .env (DB path, scan folders, API key)
│   ├── database.py      # SQLAlchemy engine + SessionLocal + get_db dependency
│   ├── models.py        # Pieza + Archivo ORM models
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── crud.py          # All DB operations
│   ├── scanner.py       # File system scan logic (pure functions, no DB)
│   ├── csv_import.py    # Import from inventario_portafolio.csv
│   ├── agent.py         # Claude API chat agent + tool implementations
│   └── routers/
│       ├── __init__.py
│       ├── catalog.py   # /api/piezas CRUD + search endpoints
│       ├── scanner.py   # /api/scan endpoints
│       └── chat.py      # /api/chat endpoint
├── frontend/
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html          # Catalog list with filters
│   │   ├── detail.html         # Piece detail + edit
│   │   ├── add.html            # Manual add form
│   │   ├── scan_review.html    # Post-scan confirmation
│   │   └── partials/
│   │       ├── piece_list.html # HTMX swap target for filter/search
│   │       └── chat_message.html
│   └── static/
│       ├── style.css
│       └── chat.js
├── tests/
│   ├── conftest.py      # in-memory SQLite DB fixture + test client
│   ├── test_crud.py
│   ├── test_scanner.py
│   ├── test_csv_import.py
│   ├── test_api_catalog.py
│   ├── test_api_scanner.py
│   └── test_agent_tools.py
├── docs/superpowers/plans/2026-11-11-partituras-catalog.md
├── requirements.txt
├── .env.example
└── run.sh
```

---

## Task 1: Project Bootstrap + DB Models + CRUD

**Files:**
- Create: `app/__init__.py`, `app/config.py`, `app/database.py`, `app/models.py`, `app/schemas.py`, `app/crud.py`, `requirements.txt`, `.env.example`
- Create: `tests/conftest.py`, `tests/test_crud.py`

**Interfaces:**
- Produces:
  - `get_db() -> Generator[Session, None, None]` (FastAPI dependency)
  - `crud.create_pieza(db, pieza: PiezaCreate) -> Pieza`
  - `crud.get_pieza(db, pieza_id: int) -> Pieza | None`
  - `crud.list_piezas(db, skip=0, limit=50, composer=None, instrument=None, difficulty=None, location_type=None) -> list[Pieza]`
  - `crud.search_piezas(db, query: str, skip=0, limit=50) -> list[Pieza]`
  - `crud.update_pieza(db, pieza_id: int, data: dict) -> Pieza | None`
  - `crud.delete_pieza(db, pieza_id: int) -> bool`
  - `crud.add_archivo(db, pieza_id: int, archivo: ArchivoCreate) -> Archivo`
  - `crud.remove_archivo(db, archivo_id: int) -> bool`
  - `crud.get_archivo_by_path(db, path: str) -> Archivo | None`

- [ ] **Step 1: Write `requirements.txt`**

```
fastapi>=0.111
uvicorn[standard]>=0.29
sqlalchemy>=2.0
pydantic>=2.0
anthropic>=0.25
python-dotenv>=1.0
jinja2>=3.1
aiofiles>=23.0
httpx>=0.27
pytest>=8.0
pytest-asyncio>=0.23
```

- [ ] **Step 2: Write `app/config.py`**

```python
class Settings(BaseSettings):
    db_path: str = "partituras.db"
    scan_folders: list[str] = []
    anthropic_api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

- [ ] **Step 3: Write `app/database.py`**

Engine from `settings.db_path`, `SessionLocal`, `Base = declarative_base()`, `get_db()` dependency that yields a session and closes it.

- [ ] **Step 4: Write `app/models.py` — failing test first**

```python
# tests/test_crud.py
def test_create_tables(db):
    from app.models import Pieza, Archivo
    inspector = inspect(db.bind)
    assert "piezas" in inspector.get_table_names()
    assert "archivos" in inspector.get_table_names()
```

- [ ] **Step 5: Run test to verify it fails**

```bash
cd ~/Documents/Proyectos/partituras-app && pytest tests/test_crud.py::test_create_tables -v
```
Expected: FAIL with ImportError or AssertionError

- [ ] **Step 6: Implement `app/models.py`**

`Pieza`: `id` (PK), `title` (String, not null, indexed), `composer` (String, nullable), `instruments` (String, nullable — JSON-encoded list), `genre` (String, nullable), `difficulty` (String, nullable), `notes` (Text, nullable), `created_at` (DateTime, default=utcnow)

`Archivo`: `id` (PK), `pieza_id` (FK → piezas.id, cascade delete), `format` (String), `location_type` (String), `path` (String, nullable, unique when not null), `last_modified` (DateTime, nullable), `created_at` (DateTime, default=utcnow)

- [ ] **Step 7: Write `app/schemas.py`**

`ArchivoCreate`, `ArchivoRead(ArchivoCreate)` (adds `id`, `pieza_id`, `created_at`); `PiezaCreate`, `PiezaRead(PiezaCreate)` (adds `id`, `archivos: list[ArchivoRead]`, `created_at`); `PiezaUpdate` (all fields optional).

- [ ] **Step 8: Write CRUD tests**

```python
def test_create_and_get_pieza(db):
    pieza = crud.create_pieza(db, PiezaCreate(title="Cielito Lindo", composer="Quirino Mendoza"))
    assert pieza.id is not None
    fetched = crud.get_pieza(db, pieza.id)
    assert fetched.title == "Cielito Lindo"

def test_search_piezas_fuzzy(db):
    crud.create_pieza(db, PiezaCreate(title="Canción de Cuna"))
    results = crud.search_piezas(db, "cancion")  # no accent
    assert len(results) == 1

def test_add_archivo_to_pieza(db):
    pieza = crud.create_pieza(db, PiezaCreate(title="Test"))
    archivo = crud.add_archivo(db, pieza.id, ArchivoCreate(format="pdf", location_type="mac", path="/tmp/test.pdf"))
    assert archivo.pieza_id == pieza.id

def test_list_piezas_filter_by_location(db):
    p = crud.create_pieza(db, PiezaCreate(title="X"))
    crud.add_archivo(db, p.id, ArchivoCreate(format="pdf", location_type="icloud", path="/icloud/x.pdf"))
    results = crud.list_piezas(db, location_type="icloud")
    assert any(r.id == p.id for r in results)

def test_delete_pieza_cascades(db):
    p = crud.create_pieza(db, PiezaCreate(title="Del"))
    crud.add_archivo(db, p.id, ArchivoCreate(format="pdf", location_type="mac", path="/tmp/del.pdf"))
    crud.delete_pieza(db, p.id)
    assert crud.get_pieza(db, p.id) is None
```

- [ ] **Step 9: Run tests to verify they fail**

```bash
pytest tests/test_crud.py -v
```
Expected: FAILs (crud.py not written yet)

- [ ] **Step 10: Implement `app/crud.py`**

`search_piezas` must normalize accented characters: apply `unicodedata.normalize('NFD')` + strip combining chars on both query and stored title before comparing (use `LOWER()` via SQLAlchemy's `func.lower` and Python-side unidecode, or store a `title_normalized` column — builder's choice).

- [ ] **Step 11: Run all CRUD tests to verify pass**

```bash
pytest tests/test_crud.py -v
```
Expected: all PASS

- [ ] **Step 12: Write `tests/conftest.py`**

In-memory SQLite engine (`sqlite:///:memory:`), create all tables, yield `SessionLocal()`, drop all tables after test. Export as `db` fixture with `scope="function"`.

- [ ] **Step 13: Write `.env.example`**

```
DB_PATH=partituras.db
SCAN_FOLDERS=~/Documents/Musica,~/Library/Mobile Documents/com~apple~CloudDocs
ANTHROPIC_API_KEY=sk-ant-...
PORT=8000
```

- [ ] **Step 14: Commit**

```bash
git init && git add -A && git commit -m "feat: project bootstrap, DB models, CRUD with tests"
```

---

## Task 2: File Scanner + CSV Import

**Files:**
- Create: `app/scanner.py`, `app/csv_import.py`
- Create: `tests/test_scanner.py`, `tests/test_csv_import.py`

**Interfaces:**
- Consumes: nothing from app (pure functions)
- Produces:
  - `ScanCandidate` dataclass: `path: str`, `inferred_title: str`, `inferred_composer: str | None`, `format: str`, `location_type: str`
  - `scanner.scan_folder(folder_path: str) -> list[ScanCandidate]`
  - `scanner.parse_filename(stem: str) -> tuple[str, str | None]`  → `(title, composer_or_None)`
  - `csv_import.import_csv(db: Session, csv_path: str) -> tuple[int, int]`  → `(created, skipped)`

- [ ] **Step 1: Write failing scanner tests**

```python
def test_parse_filename_composer_title():
    title, composer = parse_filename("Bach - Suite No.1")
    assert title == "Suite No.1"
    assert composer == "Bach"

def test_parse_filename_title_only():
    title, composer = parse_filename("Cielito_Lindo")
    assert title == "Cielito Lindo"
    assert composer is None

def test_parse_filename_strips_leading_numbers():
    title, _ = parse_filename("01 - La Bikina")
    assert title == "La Bikina"

def test_scan_folder_finds_music_files(tmp_path):
    (tmp_path / "Bach - Suite.pdf").write_bytes(b"")
    (tmp_path / "notas.txt").write_bytes(b"")
    results = scan_folder(str(tmp_path))
    assert len(results) == 1
    assert results[0].format == "pdf"

def test_scan_folder_detects_icloud_path():
    icloud_root = str(Path.home() / "Library/Mobile Documents/com~apple~CloudDocs")
    candidate = ScanCandidate(
        path=f"{icloud_root}/piece.mscz",
        inferred_title="piece",
        inferred_composer=None,
        format="mscz",
        location_type="icloud",
    )
    assert candidate.location_type == "icloud"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scanner.py -v
```

- [ ] **Step 3: Implement `app/scanner.py`**

`parse_filename`: strip leading `\d+[\s\-\.]+`; if `" - "` in stem split into `(composer, title)` else title = stem with `_` → space. `scan_folder`: walk with `os.walk`, yield `ScanCandidate` for files whose suffix (lowercase) is in the allowed set. `location_type`: `"icloud"` if path starts with `str(Path.home() / "Library/Mobile Documents/com~apple~CloudDocs")`, else `"mac"`.

- [ ] **Step 4: Run scanner tests to verify pass**

```bash
pytest tests/test_scanner.py -v
```

- [ ] **Step 5: Write failing CSV import tests**

```python
def test_import_csv_creates_piezas(db, tmp_path):
    csv_content = (
        "archivo,titulo,subtitulo,compositor,arreglista,instrumentos,n_instrumentos,"
        "tonalidad,tempo_bpm,n_compases,tiene_acordes,genero,servicio,carpeta,error\n"
        "BFJLA/Test.mscz,Mi Canción,,Juan Pérez,,Flauta; Trompeta,2,,120,10,no,banda/oaxaqueña,arreglo para grupo,BFJLA,\n"
    )
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)
    created, skipped = import_csv(db, str(csv_file))
    assert created == 1
    assert skipped == 0
    piezas = crud.list_piezas(db)
    assert piezas[0].title == "Mi Canción"
    assert piezas[0].composer == "Juan Pérez"

def test_import_csv_skips_duplicates(db, tmp_path):
    # run import twice — second run must not create duplicates
    ...  # same csv, assert created=1, skipped=1 on second run
```

- [ ] **Step 6: Implement `app/csv_import.py`**

Read CSV with `csv.DictReader`. For each row: build `PiezaCreate` from `titulo`, `compositor`, `instrumentos` (split on `"; "`), `genero`. Map `archivo` path prefix to base folder + `".mscz"` extension → `ArchivoCreate(format="mscz", location_type="mac", path=…)`. Check if a Pieza with same title + composer already exists (via `crud.search_piezas` exact match) — if yes, skip. Use `~/Documents/Musica/` as the base path for relative paths in the CSV.

- [ ] **Step 7: Run CSV import tests to verify pass**

```bash
pytest tests/test_csv_import.py -v
```

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "feat: file scanner and CSV import"
```

---

## Task 3: REST API — Catalog CRUD + Search

**Files:**
- Create: `app/main.py`, `app/routers/__init__.py`, `app/routers/catalog.py`
- Create: `tests/test_api_catalog.py`

**Interfaces:**
- Consumes: `get_db`, all `crud.*` functions, `PiezaCreate`, `PiezaRead`, `PiezaUpdate`
- Produces HTTP endpoints:
  - `GET /api/piezas` → `list[PiezaRead]` (params: `skip`, `limit`, `composer`, `instrument`, `difficulty`, `location_type`)
  - `GET /api/piezas/search?q=` → `list[PiezaRead]`
  - `POST /api/piezas` → `PiezaRead` (201)
  - `GET /api/piezas/{id}` → `PiezaRead`
  - `PATCH /api/piezas/{id}` → `PiezaRead`
  - `DELETE /api/piezas/{id}` → 204
  - `POST /api/piezas/{id}/archivos` → `ArchivoRead` (201)
  - `DELETE /api/archivos/{id}` → 204

- [ ] **Step 1: Write failing API tests**

```python
def test_create_pieza_api(client):
    r = client.post("/api/piezas", json={"title": "Jarabe Tapatío"})
    assert r.status_code == 201
    assert r.json()["title"] == "Jarabe Tapatío"

def test_list_piezas_pagination(client):
    for i in range(10):
        client.post("/api/piezas", json={"title": f"Pieza {i}"})
    r = client.get("/api/piezas?skip=0&limit=5")
    assert len(r.json()) == 5

def test_search_piezas_api(client):
    client.post("/api/piezas", json={"title": "El Son de la Negra"})
    r = client.get("/api/piezas/search?q=negra")
    assert len(r.json()) >= 1

def test_delete_pieza_api(client):
    r = client.post("/api/piezas", json={"title": "Temp"})
    pieza_id = r.json()["id"]
    r2 = client.delete(f"/api/piezas/{pieza_id}")
    assert r2.status_code == 204

def test_add_archivo_to_pieza_api(client):
    r = client.post("/api/piezas", json={"title": "Con Archivo"})
    pieza_id = r.json()["id"]
    r2 = client.post(f"/api/piezas/{pieza_id}/archivos", json={
        "format": "pdf", "location_type": "mac", "path": "/tmp/x.pdf"
    })
    assert r2.status_code == 201
    assert r2.json()["pieza_id"] == pieza_id
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_api_catalog.py -v
```

- [ ] **Step 3: Implement `app/main.py`**

`app = FastAPI(title="Partituras")`, `Base.metadata.create_all(engine)` on startup, mount `StaticFiles` at `/static`, include `Jinja2Templates` for `frontend/templates/`, register `catalog_router`, `scanner_router`, `chat_router`.

- [ ] **Step 4: Implement `app/routers/catalog.py`**

Standard FastAPI router with `APIRouter(prefix="/api")`. All endpoints call their corresponding `crud.*` function. `GET /piezas/{id}` raises `HTTPException(404)` when `get_pieza` returns None. `PATCH` passes only the provided (non-None) fields to `crud.update_pieza`.

- [ ] **Step 5: Run API tests to verify pass**

```bash
pytest tests/test_api_catalog.py -v
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: catalog REST API"
```

---

## Task 4: REST API — Scanner Flow

**Files:**
- Create: `app/routers/scanner.py`
- Create: `tests/test_api_scanner.py`

**Interfaces:**
- Consumes: `scanner.scan_folder`, `crud.create_pieza`, `crud.add_archivo`, `crud.get_archivo_by_path`, `ScanCandidate`
- Produces HTTP endpoints:
  - `POST /api/scan` body `{"folders": ["path1", ...]}` → `{"job_id": str, "count": int, "candidates": list[ScanCandidateResponse]}`
  - `POST /api/scan/confirm` body `{"candidates": [{"inferred_title": str, "inferred_composer": str|null, "format": str, "location_type": str, "path": str}]}` → `{"created": int, "skipped": int}`

Scan results live in a module-level dict keyed by `job_id` (UUID4 string); no background job queue needed.

- [ ] **Step 1: Write failing tests**

```python
def test_scan_returns_candidates(client, tmp_path):
    (tmp_path / "Bach - Fuga.pdf").write_bytes(b"")
    r = client.post("/api/scan", json={"folders": [str(tmp_path)]})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["candidates"][0]["inferred_title"] == "Fuga"

def test_confirm_creates_piezas(client, tmp_path):
    (tmp_path / "Mozart - Sonata.mscz").write_bytes(b"")
    scan_r = client.post("/api/scan", json={"folders": [str(tmp_path)]})
    candidates = scan_r.json()["candidates"]
    r = client.post("/api/scan/confirm", json={"candidates": candidates})
    assert r.json()["created"] == 1

def test_confirm_skips_existing_path(client, tmp_path):
    (tmp_path / "Vals.pdf").write_bytes(b"")
    scan_r = client.post("/api/scan", json={"folders": [str(tmp_path)]})
    candidates = scan_r.json()["candidates"]
    client.post("/api/scan/confirm", json={"candidates": candidates})
    r2 = client.post("/api/scan/confirm", json={"candidates": candidates})
    assert r2.json()["skipped"] == 1
    assert r2.json()["created"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_api_scanner.py -v
```

- [ ] **Step 3: Implement `app/routers/scanner.py`**

`POST /api/scan`: call `scan_folder` for each folder, store candidates in `_scan_jobs[job_id]`, return `job_id` + serialized candidates. `POST /api/scan/confirm`: for each candidate, call `crud.get_archivo_by_path`; if path exists, increment `skipped`; else call `crud.create_pieza` + `crud.add_archivo`, increment `created`. Return `{"created": n, "skipped": m}`.

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_api_scanner.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: scanner flow API"
```

---

## Task 5: Chat Agent

**Files:**
- Create: `app/agent.py`, `app/routers/chat.py`
- Create: `tests/test_agent_tools.py`

**Interfaces:**
- Consumes: `crud.*`, `get_db`, Anthropic SDK
- Produces:
  - `agent.run_agent(db: Session, messages: list[dict]) -> str`
  - `POST /api/chat` body `{"messages": [{"role": "user"|"assistant", "content": str}]}` → `{"response": str}`

- [ ] **Step 1: Write tool-implementation tests (no API calls)**

```python
def test_tool_search_catalog(db):
    crud.create_pieza(db, PiezaCreate(title="Danzón No. 2", composer="Márquez"))
    from app.agent import tool_search_catalog
    result = tool_search_catalog(db, query="danzon")
    assert "Danzón No. 2" in result

def test_tool_filter_by_composer(db):
    crud.create_pieza(db, PiezaCreate(title="Vals", composer="Zyman"))
    from app.agent import tool_filter_by_composer
    result = tool_filter_by_composer(db, composer="Zyman")
    assert "Vals" in result

def test_tool_filter_by_location(db):
    p = crud.create_pieza(db, PiezaCreate(title="X"))
    crud.add_archivo(db, p.id, ArchivoCreate(format="pdf", location_type="papel"))
    from app.agent import tool_filter_by_location
    result = tool_filter_by_location(db, location_type="papel")
    assert "X" in result

def test_tool_returns_no_results_message(db):
    from app.agent import tool_search_catalog
    result = tool_search_catalog(db, query="xyz_nonexistent_xyz")
    assert "no encontré" in result.lower() or "no hay" in result.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_agent_tools.py -v
```

- [ ] **Step 3: Implement `app/agent.py`**

Define tool functions as plain Python (not async):
- `tool_search_catalog(db, query: str) -> str` — calls `crud.search_piezas`, formats result as a Spanish bulleted list including title, composer, locations
- `tool_filter_by_composer(db, composer: str) -> str`
- `tool_filter_by_instrument(db, instrument: str) -> str` — searches `instruments` JSON field
- `tool_filter_by_location(db, location_type: str) -> str`
- `tool_get_piece_detail(db, pieza_id: int) -> str`

Build Anthropic `tools` list from these functions. `run_agent(db, messages)`: call `anthropic.Anthropic().messages.create` with `model="claude-sonnet-4-6"`, system prompt in Spanish ("Eres un asistente personal que ayuda a gestionar una colección de partituras musicales…"), tools list, and `messages`. Handle `tool_use` stop_reason: execute tool, append `tool_result`, call API again. Return final text.

- [ ] **Step 4: Run tool tests to verify pass**

```bash
pytest tests/test_agent_tools.py -v
```

- [ ] **Step 5: Implement `app/routers/chat.py`**

`POST /api/chat`: accept `{"messages": [...]}`, call `agent.run_agent(db, messages)`, return `{"response": text}`.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: chat agent with Claude API and tool calling"
```

---

## Task 6: Frontend — Catalog UI

**Files:**
- Create: `frontend/templates/base.html`, `frontend/templates/index.html`, `frontend/templates/detail.html`, `frontend/templates/add.html`, `frontend/templates/partials/piece_list.html`
- Create: `frontend/static/style.css`
- Modify: `app/main.py` (add template routes)
- Modify: `app/routers/catalog.py` (add HTML routes alongside JSON API)

**Interfaces:**
- Consumes: all catalog API endpoints, `Jinja2Templates`

- [ ] **Step 1: Add HTML routes to `app/main.py` and `app/routers/catalog.py`**

`GET /` → renders `index.html` with first page of piezas and filter options (composers list, instruments list, locations list).  
`GET /piezas/{id}` → renders `detail.html`.  
`GET /agregar` → renders `add.html`.  
`GET /partials/piezas` → HTMX target, renders `partials/piece_list.html` (accepts same filter params as `/api/piezas`).

- [ ] **Step 2: Write `frontend/templates/base.html`**

Include HTMX (`<script src="https://unpkg.com/htmx.org@1.9.12">`), link `style.css`, define `{% block content %}` and `{% block chat %}`.

- [ ] **Step 3: Write `frontend/templates/index.html`**

Extends `base.html`. Filter sidebar: dropdowns for compositor, instrumento, dificultad, ubicación — each with `hx-get="/partials/piezas"` and `hx-target="#piece-list"`. Search bar: text input `hx-get="/partials/piezas" hx-trigger="keyup changed delay:300ms"`. Main area: `<div id="piece-list">` with partial included. Floating chat button that shows/hides `#chat-panel`.

- [ ] **Step 4: Write `frontend/templates/partials/piece_list.html`**

Renders a table or card grid of `piezas`. Each row: title, composer, instruments (truncated), locations (badge per location_type), link to detail. Include pagination links.

- [ ] **Step 5: Write `frontend/templates/detail.html`**

Piece metadata with inline edit form (HTMX `hx-patch`). List of archivos with delete button per archivo. "Agregar archivo" inline form.

- [ ] **Step 6: Write `frontend/templates/add.html`**

Form with fields: título (required), compositor, instrumentos (comma-separated), género, dificultad, notas. Archivo section: format select, location_type select, path input (optional). `POST /api/piezas` then redirect to detail.

- [ ] **Step 7: Write `frontend/static/style.css`**

Minimal CSS: sidebar layout, card/table styles, location badges (color per type), chat panel positioning. No external CSS framework dependency.

- [ ] **Step 8: Manual smoke test**

```bash
cd ~/Documents/Proyectos/partituras-app && python -m uvicorn app.main:app --reload
```
Open `http://localhost:8000`. Verify: list loads, filters work via HTMX, detail page opens, manual add form creates a piece.

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat: catalog web UI with HTMX"
```

---

## Task 7: Frontend — Scanner Review UI

**Files:**
- Create: `frontend/templates/scan_review.html`
- Modify: `app/main.py` (add `GET /escanear` route)

- [ ] **Step 1: Add `GET /escanear` route to `app/main.py`**

Renders `scan_review.html` with no data (scan not started yet).

- [ ] **Step 2: Write `frontend/templates/scan_review.html`**

Page sections:
1. **Configure scan:** textarea with one folder path per line (pre-filled from `settings.scan_folders`), "Iniciar escaneo" button → `hx-post="/api/scan"` → replaces `#scan-results`
2. **Results table** (`id="scan-results"`): checkbox per candidate, columns: título inferido, compositor inferido, formato, ruta, ubicación. "Seleccionar todos / Ninguno" controls.
3. **Confirm button:** `hx-post="/api/scan/confirm"` with selected candidates serialized → shows `{"created": N, "skipped": M}` message.

- [ ] **Step 3: Manual smoke test**

Navigate to `http://localhost:8000/escanear`. Enter `~/Documents/Musica`. Click scan. Verify candidates appear. Select a few. Click confirm. Navigate to catalog and verify they appear.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: scanner review UI"
```

---

## Task 8: Frontend — Chat Panel + Configuration + Startup

**Files:**
- Create: `frontend/static/chat.js`, `frontend/templates/partials/chat_message.html`
- Create: `run.sh`
- Modify: `frontend/templates/base.html` (add chat panel HTML + link chat.js)

- [ ] **Step 1: Write `frontend/templates/partials/chat_message.html`**

Renders a single message bubble: `role` determines alignment (user right, assistant left). Assistant messages support basic markdown (bold via `<strong>`, line breaks).

- [ ] **Step 2: Write chat panel HTML in `base.html`**

`<div id="chat-panel">`: header "Asistente de Partituras", message history `<div id="chat-messages">`, input textarea + send button. Initially hidden, shown by toggle button in index.

- [ ] **Step 3: Write `frontend/static/chat.js`**

On send: append user message to `#chat-messages`, call `fetch('/api/chat', {method: 'POST', body: JSON.stringify({messages: history})})`, append assistant response. Maintain `history` array in memory (max 20 messages).

- [ ] **Step 4: Write `run.sh`**

```bash
#!/bin/bash
cd "$(dirname "$0")"
source .env 2>/dev/null || true
python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Make executable: `chmod +x run.sh`.

- [ ] **Step 5: Run CSV import once to populate the database**

```bash
cd ~/Documents/Proyectos/partituras-app && python -c "
from app.database import SessionLocal
from app.csv_import import import_csv
db = SessionLocal()
created, skipped = import_csv(db, '~/Documents/Musica/inventario_portafolio.csv')
print(f'Importadas: {created}, omitidas: {skipped}')
db.close()
"
```
Expected: `Importadas: 309, omitidas: 0`

- [ ] **Step 6: End-to-end smoke test**

```bash
./run.sh
```
1. Open `http://localhost:8000` — verify 309 piezas load
2. Search "jarabe" — verify results
3. Filter by compositor — verify filtered list
4. Open chat — ask "¿Qué tengo de Bach?" — verify agent responds in Spanish with results
5. Run scanner on `~/Documents/Musica` — verify candidates appear, confirm a few
6. Access from iPad/phone via `http://<mac-ip>:8000` — verify loads

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: chat panel, run script, initial CSV import"
```

---

## Verification Checklist

- [ ] `pytest` passes with 0 failures
- [ ] 309 piezas imported from CSV on first run
- [ ] Search "cancion" matches "Canción" (accent-insensitive)
- [ ] Re-scanning `~/Documents/Musica` twice doesn't create duplicates
- [ ] Chat answers "¿Qué tengo de Bach?" correctly in Spanish
- [ ] App accessible at `http://<mac-ip>:8000` from another device on WiFi
- [ ] Catalog list renders 10,000+ entries without timeout (paginated at 50/page)
