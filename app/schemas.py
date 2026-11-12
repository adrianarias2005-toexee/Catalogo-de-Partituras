# Esquemas Pydantic para validación y serialización de datos
import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Archivo
# ---------------------------------------------------------------------------

class ArchivoCreate(BaseModel):
    """Datos necesarios para crear un archivo."""

    format: str
    location_type: str
    path: Optional[str] = None
    last_modified: Optional[datetime] = None


class ArchivoRead(ArchivoCreate):
    """Datos de un archivo ya creado (incluye ID y relación)."""

    id: int
    pieza_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Pieza
# ---------------------------------------------------------------------------

class PiezaCreate(BaseModel):
    """Datos necesarios para crear una pieza musical."""

    title: str
    composer: Optional[str] = None
    instruments: list[str] = []
    genre: Optional[str] = None
    difficulty: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("instruments", mode="before")
    @classmethod
    def _deserializar_instruments(cls, v: object) -> list[str]:
        """Acepta tanto lista[str] (desde API) como cadena JSON (desde ORM)."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (ValueError, TypeError):
                pass
            return []
        return v if v is not None else []


class PiezaRead(PiezaCreate):
    """Datos de una pieza ya creada (incluye ID, archivos y fecha)."""

    id: int
    archivos: list[ArchivoRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class PiezaUpdate(BaseModel):
    """Actualización parcial de una pieza (todos los campos opcionales)."""

    title: Optional[str] = None
    composer: Optional[str] = None
    instruments: Optional[list[str]] = None
    genre: Optional[str] = None
    difficulty: Optional[str] = None
    notes: Optional[str] = None
