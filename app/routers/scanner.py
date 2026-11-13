# Router REST para el flujo de escaneo de archivos musicales
import dataclasses
import os
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.scanner import ScanCandidate, scan_folder
from app.schemas import ArchivoCreate, PiezaCreate

scanner_router = APIRouter(prefix="/api", tags=["escáner"])

# Almacén en memoria de resultados de escaneo indexados por job_id
_scan_jobs: dict[str, list[ScanCandidate]] = {}


# ---------------------------------------------------------------------------
# Esquemas de petición
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    folders: list[str]


class CandidateIn(BaseModel):
    path: str
    inferred_title: str
    inferred_composer: str | None = None
    format: str
    location_type: str


class ConfirmRequest(BaseModel):
    candidates: list[CandidateIn]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@scanner_router.post("/scan")
def iniciar_escaneo(
    req: ScanRequest,
) -> dict:
    """Escanea las carpetas indicadas y devuelve los candidatos encontrados.

    Expande ~ en cada ruta antes de escanear.
    Almacena los resultados en memoria bajo un job_id UUID4 para uso posterior.
    """
    candidatos: list[ScanCandidate] = []
    for carpeta in req.folders:
        ruta = os.path.expanduser(carpeta)
        candidatos.extend(scan_folder(ruta))

    job_id = str(uuid.uuid4())
    _scan_jobs[job_id] = candidatos

    return {
        "job_id": job_id,
        "count": len(candidatos),
        "candidates": [dataclasses.asdict(c) for c in candidatos],
    }


@scanner_router.post("/scan/confirm")
def confirmar_escaneo(
    req: ConfirmRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Importa los candidatos confirmados al catálogo.

    - Si location_type == 'papel' o path está vacío: crea siempre (sin verificar ruta).
    - Si la ruta ya existe en la BD: incrementa skipped.
    - En otro caso: crea Pieza + Archivo e incrementa created.

    Devuelve {"created": int, "skipped": int}.
    """
    created = 0
    skipped = 0

    for candidato in req.candidates:
        # Candidatos en papel o sin ruta: siempre crear
        if candidato.location_type == "papel" or not candidato.path:
            pieza = crud.create_pieza(
                db,
                PiezaCreate(
                    title=candidato.inferred_title,
                    composer=candidato.inferred_composer,
                ),
            )
            crud.add_archivo(
                db,
                pieza.id,
                ArchivoCreate(
                    format=candidato.format,
                    location_type=candidato.location_type,
                    path=candidato.path or None,
                ),
            )
            created += 1
            continue

        # Verificar si la ruta ya existe
        existente = crud.get_archivo_by_path(db, candidato.path)
        if existente is not None:
            skipped += 1
            continue

        pieza = crud.create_pieza(
            db,
            PiezaCreate(
                title=candidato.inferred_title,
                composer=candidato.inferred_composer,
            ),
        )
        crud.add_archivo(
            db,
            pieza.id,
            ArchivoCreate(
                format=candidato.format,
                location_type=candidato.location_type,
                path=candidato.path,
            ),
        )
        created += 1

    return {"created": created, "skipped": skipped}
