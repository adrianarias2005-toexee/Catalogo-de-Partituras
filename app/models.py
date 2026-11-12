# Modelos SQLAlchemy para el catálogo de partituras
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Pieza(Base):
    """Pieza musical en el catálogo."""

    __tablename__ = "piezas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # Columna normalizada (sin acentos, minúsculas) para búsqueda eficiente
    title_normalized: Mapped[str] = mapped_column(String, nullable=False, server_default="", index=True)
    composer: Mapped[str | None] = mapped_column(String, nullable=True)
    # Lista de instrumentos codificada como JSON, p.ej. '["Flauta", "Trompeta"]'
    instruments: Mapped[str | None] = mapped_column(String, nullable=True)
    genre: Mapped[str | None] = mapped_column(String, nullable=True)
    # Valores válidos: "fácil", "intermedio", "avanzado", o nulo
    difficulty: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    archivos: Mapped[list["Archivo"]] = relationship(
        "Archivo", back_populates="pieza", cascade="all, delete-orphan"
    )


class Archivo(Base):
    """Archivo físico asociado a una pieza musical."""

    __tablename__ = "archivos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pieza_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("piezas.id", ondelete="CASCADE"), nullable=False
    )
    # Valores válidos: "pdf", "musicxml", "mscz", "mscx", "sib", "musx", "capx", "papel", "otro"
    format: Mapped[str] = mapped_column(String, nullable=False)
    # Valores válidos: "mac", "icloud", "ipad", "celular", "papel"
    location_type: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    pieza: Mapped["Pieza"] = relationship("Pieza", back_populates="archivos")
