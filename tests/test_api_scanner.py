# Tests de integración para la API REST del flujo de escáner
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
# Tests de escaneo
# ---------------------------------------------------------------------------

def test_scan_returns_candidates(client, tmp_path):
    (tmp_path / "Bach - Fuga.pdf").write_bytes(b"")
    r = client.post("/api/scan", json={"folders": [str(tmp_path)]})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["candidates"][0]["inferred_title"] == "Fuga"


def test_scan_returns_job_id(client, tmp_path):
    (tmp_path / "Mozart - Sonata.mscz").write_bytes(b"")
    r = client.post("/api/scan", json={"folders": [str(tmp_path)]})
    assert r.status_code == 200
    body = r.json()
    assert "job_id" in body
    assert isinstance(body["job_id"], str)
    assert len(body["job_id"]) == 36  # UUID4


def test_scan_multiple_folders(client, tmp_path):
    folder1 = tmp_path / "folder1"
    folder2 = tmp_path / "folder2"
    folder1.mkdir()
    folder2.mkdir()
    (folder1 / "Vals.pdf").write_bytes(b"")
    (folder2 / "Mazurca.pdf").write_bytes(b"")
    r = client.post("/api/scan", json={"folders": [str(folder1), str(folder2)]})
    assert r.status_code == 200
    assert r.json()["count"] == 2


def test_scan_ignores_non_music_files(client, tmp_path):
    (tmp_path / "notas.txt").write_bytes(b"")
    (tmp_path / "imagen.jpg").write_bytes(b"")
    (tmp_path / "Fuga.pdf").write_bytes(b"")
    r = client.post("/api/scan", json={"folders": [str(tmp_path)]})
    assert r.status_code == 200
    assert r.json()["count"] == 1


# ---------------------------------------------------------------------------
# Tests de confirmación
# ---------------------------------------------------------------------------

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


def test_confirm_mixed_new_and_existing(client, tmp_path):
    (tmp_path / "Beethoven - Sonata.pdf").write_bytes(b"")
    (tmp_path / "Chopin - Nocturno.pdf").write_bytes(b"")
    scan_r = client.post("/api/scan", json={"folders": [str(tmp_path)]})
    candidates = scan_r.json()["candidates"]
    # Confirmar solo el primero
    client.post("/api/scan/confirm", json={"candidates": [candidates[0]]})
    # Confirmar ambos: el primero debe omitirse, el segundo crearse
    r2 = client.post("/api/scan/confirm", json={"candidates": candidates})
    assert r2.json()["created"] == 1
    assert r2.json()["skipped"] == 1


def test_confirm_papel_always_creates(client, tmp_path):
    """Candidatos con location_type='papel' siempre se crean (sin chequeo de ruta)."""
    candidato_papel = {
        "path": "",
        "inferred_title": "Partitura Papel",
        "inferred_composer": "Autor",
        "format": "pdf",
        "location_type": "papel",
    }
    r1 = client.post("/api/scan/confirm", json={"candidates": [candidato_papel]})
    assert r1.json()["created"] == 1
    # Segunda vez: también debe crear (no hace chequeo de ruta para papel)
    r2 = client.post("/api/scan/confirm", json={"candidates": [candidato_papel]})
    assert r2.json()["created"] == 1
