# Tests de integración para la API REST del catálogo de partituras
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


# ---------------------------------------------------------------------------
# Fixture: base de datos en memoria + cliente de prueba
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def client():
    """Cliente de prueba con base de datos SQLite en memoria.

    Usa StaticPool para que todas las conexiones compartan el mismo
    almacenamiento en memoria (SQLite in-memory es per-conexión por defecto).
    """
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


# ---------------------------------------------------------------------------
# Tests de creación
# ---------------------------------------------------------------------------

def test_create_pieza_api(client):
    r = client.post("/api/piezas", json={"title": "Jarabe Tapatío"})
    assert r.status_code == 201
    assert r.json()["title"] == "Jarabe Tapatío"


def test_create_pieza_devuelve_id(client):
    r = client.post("/api/piezas", json={"title": "El Jarabe Tapatío", "composer": "Autor Desconocido"})
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["composer"] == "Autor Desconocido"


# ---------------------------------------------------------------------------
# Tests de listado y paginación
# ---------------------------------------------------------------------------

def test_list_piezas_pagination(client):
    for i in range(10):
        client.post("/api/piezas", json={"title": f"Pieza {i}"})
    r = client.get("/api/piezas?skip=0&limit=5")
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_list_piezas_sin_filtros(client):
    client.post("/api/piezas", json={"title": "Vals Chido"})
    r = client.get("/api/piezas")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_list_piezas_filtro_compositor(client):
    client.post("/api/piezas", json={"title": "Obra A", "composer": "Beethoven"})
    client.post("/api/piezas", json={"title": "Obra B", "composer": "Mozart"})
    r = client.get("/api/piezas?composer=beethoven")
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) >= 1
    assert all("beethoven" in d["composer"].lower() for d in datos)


def test_list_piezas_filtro_dificultad(client):
    client.post("/api/piezas", json={"title": "Fácil", "difficulty": "beginner"})
    client.post("/api/piezas", json={"title": "Difícil", "difficulty": "advanced"})
    r = client.get("/api/piezas?difficulty=beginner")
    assert r.status_code == 200
    datos = r.json()
    assert all(d["difficulty"] == "beginner" for d in datos)


# ---------------------------------------------------------------------------
# Tests de búsqueda
# ---------------------------------------------------------------------------

def test_search_piezas_api(client):
    client.post("/api/piezas", json={"title": "El Son de la Negra"})
    r = client.get("/api/piezas/search?q=negra")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_search_piezas_insensible_acentos(client):
    client.post("/api/piezas", json={"title": "Canción de Cuna"})
    r = client.get("/api/piezas/search?q=cancion")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_search_piezas_sin_resultados(client):
    r = client.get("/api/piezas/search?q=xyzNoExiste")
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# Tests de lectura individual
# ---------------------------------------------------------------------------

def test_get_pieza_api(client):
    r = client.post("/api/piezas", json={"title": "Lectura Individual"})
    pieza_id = r.json()["id"]
    r2 = client.get(f"/api/piezas/{pieza_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == pieza_id


def test_get_pieza_no_existe(client):
    r = client.get("/api/piezas/9999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests de actualización
# ---------------------------------------------------------------------------

def test_patch_pieza_api(client):
    r = client.post("/api/piezas", json={"title": "Original"})
    pieza_id = r.json()["id"]
    r2 = client.patch(f"/api/piezas/{pieza_id}", json={"title": "Actualizado"})
    assert r2.status_code == 200
    assert r2.json()["title"] == "Actualizado"


def test_patch_pieza_parcial(client):
    r = client.post("/api/piezas", json={"title": "Vals", "composer": "Autor"})
    pieza_id = r.json()["id"]
    r2 = client.patch(f"/api/piezas/{pieza_id}", json={"difficulty": "intermediate"})
    assert r2.status_code == 200
    data = r2.json()
    assert data["difficulty"] == "intermediate"
    assert data["composer"] == "Autor"  # campo no tocado se conserva


def test_patch_pieza_no_existe(client):
    r = client.patch("/api/piezas/9999", json={"title": "Nada"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests de borrado
# ---------------------------------------------------------------------------

def test_delete_pieza_api(client):
    r = client.post("/api/piezas", json={"title": "Temp"})
    pieza_id = r.json()["id"]
    r2 = client.delete(f"/api/piezas/{pieza_id}")
    assert r2.status_code == 204


def test_delete_pieza_ya_borrada(client):
    r = client.post("/api/piezas", json={"title": "Efímera"})
    pieza_id = r.json()["id"]
    client.delete(f"/api/piezas/{pieza_id}")
    r2 = client.delete(f"/api/piezas/{pieza_id}")
    assert r2.status_code == 404


def test_delete_pieza_no_existe(client):
    r = client.delete("/api/piezas/9999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests de archivos
# ---------------------------------------------------------------------------

def test_add_archivo_to_pieza_api(client):
    r = client.post("/api/piezas", json={"title": "Con Archivo"})
    pieza_id = r.json()["id"]
    r2 = client.post(f"/api/piezas/{pieza_id}/archivos", json={
        "format": "pdf", "location_type": "mac", "path": "/tmp/x.pdf"
    })
    assert r2.status_code == 201
    assert r2.json()["pieza_id"] == pieza_id


def test_add_archivo_pieza_no_existe(client):
    r = client.post("/api/piezas/9999/archivos", json={
        "format": "pdf", "location_type": "mac", "path": "/tmp/y.pdf"
    })
    assert r.status_code == 404


def test_delete_archivo_api(client):
    r = client.post("/api/piezas", json={"title": "Con Archivo para Borrar"})
    pieza_id = r.json()["id"]
    r2 = client.post(f"/api/piezas/{pieza_id}/archivos", json={
        "format": "pdf", "location_type": "mac", "path": "/tmp/z.pdf"
    })
    archivo_id = r2.json()["id"]
    r3 = client.delete(f"/api/archivos/{archivo_id}")
    assert r3.status_code == 204


def test_delete_archivo_no_existe(client):
    r = client.delete("/api/archivos/9999")
    assert r.status_code == 404
