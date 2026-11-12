# Configuración de pruebas: fixture de base de datos en memoria
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base


# Motor SQLite en memoria compartido para inspecciones en pruebas
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)


@pytest.fixture(scope="function")
def db():
    """Base de datos SQLite en memoria para pruebas aisladas."""
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
