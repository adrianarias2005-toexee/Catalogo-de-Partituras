# Operaciones CRUD para el catálogo de partituras
import json
import unicodedata
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Archivo, Pieza
from app.schemas import ArchivoCreate, PiezaCreate


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    """Convierte texto a minúsculas y elimina marcas diacríticas (acentos).

    Ejemplo: 'Canción' → 'cancion'
    """
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def _instrumentos_a_json(instruments: list[str]) -> str:
    return json.dumps(instruments, ensure_ascii=False)


def _json_a_instrumentos(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return []


# ---------------------------------------------------------------------------
# CRUD — Pieza
# ---------------------------------------------------------------------------

def create_pieza(db: Session, pieza: PiezaCreate) -> Pieza:
    """Crea una nueva pieza musical en la base de datos."""
    db_pieza = Pieza(
        title=pieza.title,
        title_normalized=_normalizar(pieza.title),
        composer=pieza.composer,
        instruments=_instrumentos_a_json(pieza.instruments),
        genre=pieza.genre,
        difficulty=pieza.difficulty,
        notes=pieza.notes,
    )
    db.add(db_pieza)
    db.commit()
    db.refresh(db_pieza)
    return db_pieza


def get_pieza(db: Session, pieza_id: int) -> Optional[Pieza]:
    """Devuelve una pieza por su ID, o None si no existe."""
    return db.get(Pieza, pieza_id)


def list_piezas(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    composer: Optional[str] = None,
    instrument: Optional[str] = None,
    difficulty: Optional[str] = None,
    location_type: Optional[str] = None,
) -> list[Pieza]:
    """Lista piezas con filtros opcionales y paginación."""
    query = db.query(Pieza)

    if composer:
        query = query.filter(Pieza.composer.ilike(f"%{composer}%"))
    if difficulty:
        query = query.filter(Pieza.difficulty == difficulty)
    if instrument:
        # El campo instruments es JSON; usamos LIKE para filtrado básico
        query = query.filter(Pieza.instruments.ilike(f"%{instrument}%"))
    if location_type:
        query = query.join(Pieza.archivos).filter(Archivo.location_type == location_type)

    return query.offset(skip).limit(limit).all()


def search_piezas(
    db: Session, query: str, skip: int = 0, limit: int = 50
) -> list[Pieza]:
    """Busca piezas por título de forma insensible a acentos y mayúsculas.

    'cancion' encuentra 'Canción de Cuna'.
    La búsqueda se realiza contra la columna title_normalized que almacena
    el título sin acentos y en minúsculas.
    """
    term_normalizado = _normalizar(query)
    return (
        db.query(Pieza)
        .filter(Pieza.title_normalized.ilike(f"%{term_normalizado}%"))
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_pieza(db: Session, pieza_id: int, data: dict) -> Optional[Pieza]:
    """Actualiza campos de una pieza. Devuelve None si no existe."""
    db_pieza = db.get(Pieza, pieza_id)
    if db_pieza is None:
        return None
    for campo, valor in data.items():
        if campo == "instruments" and isinstance(valor, list):
            setattr(db_pieza, campo, _instrumentos_a_json(valor))
        elif campo == "title" and isinstance(valor, str):
            db_pieza.title = valor
            db_pieza.title_normalized = _normalizar(valor)
        else:
            setattr(db_pieza, campo, valor)
    db.commit()
    db.refresh(db_pieza)
    return db_pieza


def delete_pieza(db: Session, pieza_id: int) -> bool:
    """Elimina una pieza (y sus archivos en cascada). Devuelve True si existía."""
    db_pieza = db.get(Pieza, pieza_id)
    if db_pieza is None:
        return False
    db.delete(db_pieza)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# CRUD — Archivo
# ---------------------------------------------------------------------------

def add_archivo(db: Session, pieza_id: int, archivo: ArchivoCreate) -> Archivo:
    """Agrega un archivo a una pieza existente."""
    db_archivo = Archivo(
        pieza_id=pieza_id,
        format=archivo.format,
        location_type=archivo.location_type,
        path=archivo.path,
        last_modified=archivo.last_modified,
    )
    db.add(db_archivo)
    db.commit()
    db.refresh(db_archivo)
    return db_archivo


def remove_archivo(db: Session, archivo_id: int) -> bool:
    """Elimina un archivo por su ID. Devuelve True si existía."""
    db_archivo = db.get(Archivo, archivo_id)
    if db_archivo is None:
        return False
    db.delete(db_archivo)
    db.commit()
    return True


def get_archivo_by_path(db: Session, path: str) -> Optional[Archivo]:
    """Devuelve un archivo por su ruta, o None si no existe.

    Requerido por Task 4 (escáner) para verificar si un archivo ya está registrado.
    """
    return db.query(Archivo).filter(Archivo.path == path).first()
