# Router REST para el catálogo de partituras
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import ArchivoCreate, ArchivoRead, PiezaCreate, PiezaRead, PiezaUpdate

router = APIRouter(prefix="/api", tags=["catálogo"])


# ---------------------------------------------------------------------------
# Endpoints de Pieza
# ---------------------------------------------------------------------------


@router.get("/piezas/search", response_model=list[PiezaRead])
def buscar_piezas(
    q: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[PiezaRead]:
    """Busca piezas por texto en el título (insensible a acentos y mayúsculas)."""
    return crud.search_piezas(db, query=q, skip=skip, limit=limit)


@router.get("/piezas", response_model=list[PiezaRead])
def listar_piezas(
    skip: int = 0,
    limit: int = 50,
    composer: Optional[str] = None,
    instrument: Optional[str] = None,
    difficulty: Optional[str] = None,
    location_type: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[PiezaRead]:
    """Lista piezas del catálogo con filtros y paginación opcionales."""
    return crud.list_piezas(
        db,
        skip=skip,
        limit=limit,
        composer=composer,
        instrument=instrument,
        difficulty=difficulty,
        location_type=location_type,
    )


@router.post("/piezas", response_model=PiezaRead, status_code=status.HTTP_201_CREATED)
def crear_pieza(
    pieza: PiezaCreate,
    db: Session = Depends(get_db),
) -> PiezaRead:
    """Crea una nueva pieza en el catálogo."""
    return crud.create_pieza(db, pieza)


@router.get("/piezas/{pieza_id}", response_model=PiezaRead)
def obtener_pieza(
    pieza_id: int,
    db: Session = Depends(get_db),
) -> PiezaRead:
    """Obtiene una pieza por su ID."""
    pieza = crud.get_pieza(db, pieza_id)
    if pieza is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pieza no encontrada",
        )
    return pieza


@router.patch("/piezas/{pieza_id}", response_model=PiezaRead)
def actualizar_pieza(
    pieza_id: int,
    pieza_update: PiezaUpdate,
    db: Session = Depends(get_db),
) -> PiezaRead:
    """Actualiza parcialmente una pieza existente."""
    data = pieza_update.model_dump(exclude_unset=True)
    pieza = crud.update_pieza(db, pieza_id, data)
    if pieza is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pieza no encontrada",
        )
    return pieza


@router.delete("/piezas/{pieza_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_pieza(
    pieza_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """Elimina una pieza del catálogo."""
    eliminada = crud.delete_pieza(db, pieza_id)
    if not eliminada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pieza no encontrada",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Endpoints de Archivo
# ---------------------------------------------------------------------------


@router.post(
    "/piezas/{pieza_id}/archivos",
    response_model=ArchivoRead,
    status_code=status.HTTP_201_CREATED,
)
def agregar_archivo(
    pieza_id: int,
    archivo: ArchivoCreate,
    db: Session = Depends(get_db),
) -> ArchivoRead:
    """Agrega un archivo a una pieza existente."""
    pieza = crud.get_pieza(db, pieza_id)
    if pieza is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pieza no encontrada",
        )
    return crud.add_archivo(db, pieza_id, archivo)


@router.delete("/archivos/{archivo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_archivo(
    archivo_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """Elimina un archivo del catálogo."""
    eliminado = crud.remove_archivo(db, archivo_id)
    if not eliminado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
