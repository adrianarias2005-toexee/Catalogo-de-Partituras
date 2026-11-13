# Punto de entrada principal de la aplicación Partituras
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import Base, engine
from app.routers.catalog import router as catalog_router
from app.routers.chat import chat_router
from app.routers.scanner import scanner_router

# ---------------------------------------------------------------------------
# Creación de la aplicación
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Partituras",
    description="Catálogo digital de partituras musicales",
    version="0.1.0",
)

# Crear tablas en la base de datos al arrancar
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Archivos estáticos y plantillas
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(_BASE_DIR, "frontend", "static")),
    name="static",
)

templates = Jinja2Templates(directory=os.path.join(_BASE_DIR, "frontend", "templates"))

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(catalog_router)
app.include_router(scanner_router)
app.include_router(chat_router)

# ---------------------------------------------------------------------------
# Rutas HTML (web UI)
# ---------------------------------------------------------------------------

from fastapi import Request
from fastapi.responses import HTMLResponse
from typing import Optional
from app import crud
from app.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """Página principal del catálogo con filtros."""
    piezas = crud.list_piezas(db, skip=0, limit=50)

    # Obtener listas de valores únicos para los filtros
    all_piezas = crud.list_piezas(db, skip=0, limit=10000)
    composers = sorted({p.composer for p in all_piezas if p.composer})

    import json
    instruments_set: set[str] = set()
    for p in all_piezas:
        try:
            insts = json.loads(p.instruments) if isinstance(p.instruments, str) else (p.instruments or [])
            instruments_set.update(insts)
        except Exception:
            pass
    instruments = sorted(instruments_set)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "piezas": piezas,
            "composers": composers,
            "instruments": instruments,
            "skip": 0,
            "limit": 50,
            "q": None,
            "composer": None,
            "instrument": None,
            "difficulty": None,
            "location_type": None,
        },
    )


@app.get("/piezas/{pieza_id}", response_class=HTMLResponse)
def detalle_pieza(pieza_id: int, request: Request, db: Session = Depends(get_db)):
    """Página de detalle de una pieza."""
    from fastapi import HTTPException, status
    from app.schemas import PiezaRead

    pieza = crud.get_pieza(db, pieza_id)
    if pieza is None:
        raise HTTPException(status_code=404, detail="Pieza no encontrada")

    pieza_read = PiezaRead.model_validate(pieza)
    return templates.TemplateResponse(
        request,
        "detail.html",
        {"pieza": pieza_read},
    )


@app.get("/agregar", response_class=HTMLResponse)
def agregar_pieza(request: Request):
    """Formulario para agregar una nueva pieza."""
    return templates.TemplateResponse(request, "add.html")


@app.get("/escanear", response_class=HTMLResponse)
def escanear(request: Request):
    """Página de escaneo y revisión de carpetas."""
    from app.config import settings

    return templates.TemplateResponse(
        request,
        "scan_review.html",
        {"scan_folders": settings.scan_folders},
    )


@app.get("/partials/piezas", response_class=HTMLResponse)
def partial_piezas(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    q: Optional[str] = None,
    composer: Optional[str] = None,
    instrument: Optional[str] = None,
    difficulty: Optional[str] = None,
    location_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Partial HTMX: lista de piezas filtrada."""
    from app.schemas import PiezaRead

    if q:
        piezas_orm = crud.search_piezas(db, query=q, skip=skip, limit=limit)
    else:
        piezas_orm = crud.list_piezas(
            db,
            skip=skip,
            limit=limit,
            composer=composer,
            instrument=instrument,
            difficulty=difficulty,
            location_type=location_type,
        )

    piezas = [PiezaRead.model_validate(p) for p in piezas_orm]

    return templates.TemplateResponse(
        request,
        "partials/piece_list.html",
        {
            "piezas": piezas,
            "skip": skip,
            "limit": limit,
            "q": q,
            "composer": composer,
            "instrument": instrument,
            "difficulty": difficulty,
            "location_type": location_type,
        },
    )


# ---------------------------------------------------------------------------
# Punto de entrada para uvicorn
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
