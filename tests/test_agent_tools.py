# Tests para las funciones de herramientas del agente (sin llamadas a la API de Anthropic)
import pytest

from app import crud
from app.schemas import ArchivoCreate, PiezaCreate


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


def test_tool_filter_by_instrument(db):
    crud.create_pieza(db, PiezaCreate(title="Sonata para Flauta", instruments=["Flauta", "Piano"]))
    from app.agent import tool_filter_by_instrument
    result = tool_filter_by_instrument(db, instrument="Flauta")
    assert "Sonata para Flauta" in result


def test_tool_filter_by_location(db):
    p = crud.create_pieza(db, PiezaCreate(title="X"))
    crud.add_archivo(db, p.id, ArchivoCreate(format="pdf", location_type="papel"))
    from app.agent import tool_filter_by_location
    result = tool_filter_by_location(db, location_type="papel")
    assert "X" in result


def test_tool_get_piece_detail(db):
    p = crud.create_pieza(db, PiezaCreate(title="Boléro", composer="Ravel", difficulty="avanzado"))
    crud.add_archivo(db, p.id, ArchivoCreate(format="pdf", location_type="mac"))
    from app.agent import tool_get_piece_detail
    result = tool_get_piece_detail(db, pieza_id=p.id)
    assert "Boléro" in result
    assert "Ravel" in result
    assert "mac" in result


def test_tool_returns_no_results_message(db):
    from app.agent import tool_search_catalog
    result = tool_search_catalog(db, query="xyz_nonexistent_xyz")
    assert "no encontré" in result.lower() or "no hay" in result.lower()


def test_tool_filter_by_composer_no_results(db):
    from app.agent import tool_filter_by_composer
    result = tool_filter_by_composer(db, composer="CompositoresQueNoExisten")
    assert "no encontré" in result.lower() or "no hay" in result.lower()


def test_tool_filter_by_location_no_results(db):
    from app.agent import tool_filter_by_location
    result = tool_filter_by_location(db, location_type="ipad")
    assert "no encontré" in result.lower() or "no hay" in result.lower()
