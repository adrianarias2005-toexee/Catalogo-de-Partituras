# Punto de entrada principal de la aplicación Partituras
import os

from fastapi import FastAPI

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
# Routers
# ---------------------------------------------------------------------------

app.include_router(catalog_router)
app.include_router(scanner_router)
app.include_router(chat_router)

# ---------------------------------------------------------------------------
# Punto de entrada para uvicorn
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
