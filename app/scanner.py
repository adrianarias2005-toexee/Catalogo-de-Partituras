# Escáner de archivos musicales — funciones puras (sin acceso a la BD)
import os
import re
from dataclasses import dataclass
from pathlib import Path

# Extensiones de archivo musical reconocidas
EXTENSIONES_MUSICALES: frozenset[str] = frozenset(
    [".pdf", ".mxl", ".musicxml", ".mscz", ".mscx", ".sib", ".musx", ".capx"]
)

# Ruta raíz de iCloud Drive en Mac
ICLOUD_ROOT: str = str(Path.home() / "Library/Mobile Documents/com~apple~CloudDocs")

# Patrón para números iniciales: "01 - ", "02. ", "03 ", etc.
_RE_NUMERO_INICIAL = re.compile(r"^\d+[\s\-\.]+")


@dataclass
class ScanCandidate:
    """Candidato encontrado durante el escaneo del sistema de archivos.

    Atributos:
        path: Ruta absoluta al archivo.
        inferred_title: Título inferido a partir del nombre de archivo.
        inferred_composer: Compositor inferido, o None si no se pudo determinar.
        format: Extensión en minúsculas sin el punto (p.ej. "pdf", "mscz").
        location_type: "icloud" si está en iCloud Drive, "mac" en caso contrario.
    """

    path: str
    inferred_title: str
    inferred_composer: str | None
    format: str
    location_type: str


def parse_filename(stem: str) -> tuple[str, str | None]:
    """Extrae título y compositor del nombre base de un archivo (sin extensión).

    Reglas:
    1. Eliminar número inicial seguido de separadores (p.ej. "01 - " o "02. ").
    2. Si quedan dos partes separadas por " - ", la primera es el compositor y
       la segunda el título.
    3. En caso contrario, el nombre completo (con guiones bajos → espacios) es el título.

    Retorna:
        (title, composer) donde composer puede ser None.
    """
    # 1. Eliminar número inicial
    stem = _RE_NUMERO_INICIAL.sub("", stem).strip()

    # 2. Separar por " - "
    if " - " in stem:
        partes = stem.split(" - ", 1)
        compositor = partes[0].strip()
        titulo = partes[1].strip()
        return titulo, compositor

    # 3. Sin separador: solo título (guiones bajos → espacios)
    titulo = stem.replace("_", " ").strip()
    return titulo, None


def _inferir_location_type(path: str) -> str:
    """Devuelve 'icloud' si la ruta está bajo iCloud Drive, 'mac' en otro caso."""
    return "icloud" if path.startswith(ICLOUD_ROOT) else "mac"


def scan_folder(folder_path: str) -> list[ScanCandidate]:
    """Recorre recursivamente una carpeta y devuelve candidatos de archivos musicales.

    Solo se consideran archivos cuya extensión (en minúsculas) esté en
    EXTENSIONES_MUSICALES. No realiza ninguna operación de base de datos.

    Args:
        folder_path: Ruta absoluta o relativa a la carpeta a escanear.

    Returns:
        Lista de ScanCandidate ordenada por ruta.
    """
    candidatos: list[ScanCandidate] = []

    for dirpath, _dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            ruta = os.path.join(dirpath, filename)
            p = Path(filename)
            ext = p.suffix.lower()
            if ext not in EXTENSIONES_MUSICALES:
                continue
            formato = ext.lstrip(".")
            # musicxml → mantener como "musicxml"; el formato sigue la extensión
            titulo, compositor = parse_filename(p.stem)
            location_type = _inferir_location_type(ruta)
            candidatos.append(
                ScanCandidate(
                    path=ruta,
                    inferred_title=titulo,
                    inferred_composer=compositor,
                    format=formato,
                    location_type=location_type,
                )
            )

    candidatos.sort(key=lambda c: c.path)
    return candidatos
