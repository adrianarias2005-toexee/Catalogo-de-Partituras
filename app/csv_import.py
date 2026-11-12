# Importación de partituras desde CSV de inventario
import csv
import unicodedata
from pathlib import Path

from sqlalchemy.orm import Session

from app import crud
from app.models import Pieza
from app.schemas import ArchivoCreate, PiezaCreate

# Ruta base para rutas relativas del CSV
_BASE_MUSICA = Path.home() / "Documents/Musica"

# Separador de instrumentos en el CSV
_SEP_INSTRUMENTOS = "; "


def _normalizar(texto: str) -> str:
    """Convierte texto a minúsculas y elimina marcas diacríticas (acentos).

    Réplica local de crud._normalizar para no depender de un símbolo privado.
    """
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def _extension_a_formato(path_str: str) -> str:
    """Devuelve el formato basado en la extensión del archivo."""
    ext = Path(path_str).suffix.lower().lstrip(".")
    # Mapear extensiones a valores de formato permitidos
    mapa = {
        "pdf": "pdf",
        "mxl": "musicxml",
        "musicxml": "musicxml",
        "mscz": "mscz",
        "mscx": "mscx",
        "sib": "sib",
        "musx": "musx",
        "capx": "capx",
    }
    return mapa.get(ext, "otro")


def _existe_duplicado(db: Session, titulo: str, compositor: str | None) -> bool:
    """Devuelve True si ya existe una Pieza con el mismo título y compositor.

    La comparación es insensible a acentos y mayúsculas.
    """
    titulo_norm = _normalizar(titulo)
    query = db.query(Pieza).filter(Pieza.title_normalized == titulo_norm)
    if compositor:
        compositor_lower = compositor.lower()
        candidatos = query.all()
        for pieza in candidatos:
            pieza_comp = (pieza.composer or "").lower()
            if pieza_comp == compositor_lower:
                return True
        return False
    else:
        # Sin compositor: duplicado si hay pieza con mismo título y compositor nulo
        return query.filter(Pieza.composer.is_(None)).count() > 0


def import_csv(db: Session, csv_path: str) -> tuple[int, int]:
    """Importa piezas desde un archivo CSV de inventario.

    Formato esperado: columnas separadas por coma con cabecera:
        archivo,titulo,subtitulo,compositor,arreglista,instrumentos,
        n_instrumentos,tonalidad,tempo_bpm,n_compases,tiene_acordes,
        genero,servicio,carpeta,error

    La columna 'archivo' contiene rutas relativas a ~/Documents/Musica/.
    La columna 'instrumentos' usa '; ' como separador.
    Las filas con columna 'error' no vacía se omiten.

    Detecta duplicados por título+compositor (insensible a acentos y
    mayúsculas). Si la pieza ya existe, se salta sin crear archivo adicional.

    Returns:
        (created, skipped): cantidad de piezas creadas y saltadas.
    """
    created = 0
    skipped = 0

    with open(csv_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for fila in reader:
            titulo = (fila.get("titulo") or "").strip()
            if not titulo:
                skipped += 1
                continue

            # Omitir filas marcadas con error
            error = (fila.get("error") or "").strip()
            if error:
                skipped += 1
                continue

            compositor = (fila.get("compositor") or "").strip() or None

            # Verificar duplicado
            if _existe_duplicado(db, titulo, compositor):
                skipped += 1
                continue

            # Construir lista de instrumentos
            instrumentos_raw = (fila.get("instrumentos") or "").strip()
            instrumentos: list[str] = (
                [i.strip() for i in instrumentos_raw.split(_SEP_INSTRUMENTOS) if i.strip()]
                if instrumentos_raw
                else []
            )

            genero = (fila.get("genero") or "").strip() or None

            # Crear pieza
            pieza_create = PiezaCreate(
                title=titulo,
                composer=compositor,
                instruments=instrumentos,
                genre=genero,
            )
            pieza = crud.create_pieza(db, pieza_create)

            # Crear archivo asociado
            archivo_relativo = (fila.get("archivo") or "").strip()
            if archivo_relativo:
                ruta_absoluta = str(_BASE_MUSICA / archivo_relativo)
                formato = _extension_a_formato(archivo_relativo)
                archivo_create = ArchivoCreate(
                    format=formato,
                    location_type="mac",
                    path=ruta_absoluta,
                )
                crud.add_archivo(db, pieza.id, archivo_create)

            created += 1

    return created, skipped
