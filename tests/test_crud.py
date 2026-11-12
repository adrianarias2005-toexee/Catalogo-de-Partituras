# Pruebas de las operaciones CRUD del catálogo de partituras
import pytest
from sqlalchemy import inspect

from app import crud
from app.schemas import ArchivoCreate, PiezaCreate, PiezaRead


def test_create_tables(db):
    """Las tablas 'piezas' y 'archivos' deben existir tras crear la BD."""
    from app.models import Archivo, Pieza

    inspector = inspect(db.bind)
    assert "piezas" in inspector.get_table_names()
    assert "archivos" in inspector.get_table_names()


def test_create_and_get_pieza(db):
    """Crear una pieza y recuperarla por ID."""
    pieza = crud.create_pieza(db, PiezaCreate(title="Cielito Lindo", composer="Quirino Mendoza"))
    assert pieza.id is not None
    fetched = crud.get_pieza(db, pieza.id)
    assert fetched.title == "Cielito Lindo"


def test_search_piezas_fuzzy(db):
    """La búsqueda debe ser insensible a acentos: 'cancion' encuentra 'Canción de Cuna'."""
    crud.create_pieza(db, PiezaCreate(title="Canción de Cuna"))
    results = crud.search_piezas(db, "cancion")  # sin acento
    assert len(results) == 1


def test_add_archivo_to_pieza(db):
    """Agregar un archivo a una pieza existente."""
    pieza = crud.create_pieza(db, PiezaCreate(title="Test"))
    archivo = crud.add_archivo(
        db, pieza.id, ArchivoCreate(format="pdf", location_type="mac", path="/tmp/test.pdf")
    )
    assert archivo.pieza_id == pieza.id


def test_list_piezas_filter_by_location(db):
    """Listar piezas filtradas por tipo de ubicación de archivo."""
    p = crud.create_pieza(db, PiezaCreate(title="X"))
    crud.add_archivo(
        db, p.id, ArchivoCreate(format="pdf", location_type="icloud", path="/icloud/x.pdf")
    )
    results = crud.list_piezas(db, location_type="icloud")
    assert any(r.id == p.id for r in results)


def test_delete_pieza_cascades(db):
    """Eliminar una pieza también debe eliminar sus archivos (cascade)."""
    p = crud.create_pieza(db, PiezaCreate(title="Del"))
    crud.add_archivo(
        db, p.id, ArchivoCreate(format="pdf", location_type="mac", path="/tmp/del.pdf")
    )
    crud.delete_pieza(db, p.id)
    assert crud.get_pieza(db, p.id) is None


def test_pieza_read_serializa_instruments_como_lista(db):
    """PiezaRead debe serializar instruments como lista[str], no como cadena JSON."""
    pieza = crud.create_pieza(
        db, PiezaCreate(title="Concierto", instruments=["Flauta", "Piano"])
    )
    read = PiezaRead.model_validate(pieza)
    assert isinstance(read.instruments, list)
    assert read.instruments == ["Flauta", "Piano"]
