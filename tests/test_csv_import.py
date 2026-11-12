# Pruebas de importación desde CSV de inventario
import pytest

from app import crud
from app.csv_import import import_csv

# Cabecera CSV con las columnas del inventario real
CABECERA = (
    "archivo,titulo,subtitulo,compositor,arreglista,instrumentos,n_instrumentos,"
    "tonalidad,tempo_bpm,n_compases,tiene_acordes,genero,servicio,carpeta,error\n"
)


def _csv_con_filas(*filas: str) -> str:
    return CABECERA + "\n".join(filas) + "\n"


FILA_COMPLETA = (
    "BFJLA/Test.mscz,Mi Canción,,Juan Pérez,,Flauta; Trompeta,2,,120,10,"
    "no,banda/oaxaqueña,arreglo para grupo,BFJLA,"
)

FILA_SIN_COMPOSITOR = (
    "BFJLA/Otra.mscz,La Bikina,,,,,,,,,no,regional,,BFJLA,"
)


def test_import_csv_creates_piezas(db, tmp_path):
    """Importar un CSV crea la pieza y la registra correctamente."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(_csv_con_filas(FILA_COMPLETA), encoding="utf-8")

    created, skipped = import_csv(db, str(csv_file))

    assert created == 1
    assert skipped == 0

    piezas = crud.list_piezas(db)
    assert len(piezas) == 1
    assert piezas[0].title == "Mi Canción"
    assert piezas[0].composer == "Juan Pérez"


def test_import_csv_instrumentos_separados(db, tmp_path):
    """Los instrumentos separados por '; ' se importan como lista."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(_csv_con_filas(FILA_COMPLETA), encoding="utf-8")

    import_csv(db, str(csv_file))

    from app.schemas import PiezaRead
    pieza = crud.list_piezas(db)[0]
    read = PiezaRead.model_validate(pieza)
    assert "Flauta" in read.instruments
    assert "Trompeta" in read.instruments


def test_import_csv_crea_archivo_asociado(db, tmp_path):
    """Se crea un Archivo asociado a la pieza con la ruta absoluta correcta."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(_csv_con_filas(FILA_COMPLETA), encoding="utf-8")

    import_csv(db, str(csv_file))

    pieza = crud.list_piezas(db)[0]
    assert len(pieza.archivos) == 1
    archivo = pieza.archivos[0]
    assert archivo.format == "mscz"
    assert archivo.location_type == "mac"
    assert "BFJLA/Test.mscz" in archivo.path


def test_import_csv_skips_duplicates(db, tmp_path):
    """La segunda importación del mismo CSV no crea duplicados."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(_csv_con_filas(FILA_COMPLETA), encoding="utf-8")

    created1, skipped1 = import_csv(db, str(csv_file))
    assert created1 == 1
    assert skipped1 == 0

    created2, skipped2 = import_csv(db, str(csv_file))
    assert created2 == 0
    assert skipped2 == 1

    # Solo hay una pieza en la BD
    assert len(crud.list_piezas(db)) == 1


def test_import_csv_duplicado_insensible_mayusculas(db, tmp_path):
    """La detección de duplicados es insensible a mayúsculas/minúsculas."""
    fila_original = (
        "BFJLA/Test.mscz,Mi Canción,,Juan Pérez,,,,,,,"
        "no,,,BFJLA,"
    )
    fila_mayusculas = (
        "BFJLA/Test2.mscz,MI CANCIÓN,,JUAN PÉREZ,,,,,,,"
        "no,,,BFJLA,"
    )
    csv1 = tmp_path / "orig.csv"
    csv1.write_text(_csv_con_filas(fila_original), encoding="utf-8")
    csv2 = tmp_path / "dup.csv"
    csv2.write_text(_csv_con_filas(fila_mayusculas), encoding="utf-8")

    created1, skipped1 = import_csv(db, str(csv1))
    assert created1 == 1

    created2, skipped2 = import_csv(db, str(csv2))
    assert created2 == 0
    assert skipped2 == 1


def test_import_csv_sin_compositor(db, tmp_path):
    """Se puede importar una pieza sin compositor."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(_csv_con_filas(FILA_SIN_COMPOSITOR), encoding="utf-8")

    created, skipped = import_csv(db, str(csv_file))

    assert created == 1
    pieza = crud.list_piezas(db)[0]
    assert pieza.title == "La Bikina"
    assert pieza.composer is None


def test_import_csv_multiples_filas(db, tmp_path):
    """Se importan correctamente múltiples piezas de un mismo CSV."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        _csv_con_filas(FILA_COMPLETA, FILA_SIN_COMPOSITOR),
        encoding="utf-8",
    )

    created, skipped = import_csv(db, str(csv_file))

    assert created == 2
    assert skipped == 0
    assert len(crud.list_piezas(db)) == 2


def test_import_csv_fila_con_error_se_omite(db, tmp_path):
    """Las filas con columna 'error' no vacía se omiten."""
    fila_con_error = (
        "BFJLA/Error.mscz,Pieza Rota,,Compositor,,,,,,,"
        "no,,,BFJLA,archivo no encontrado"
    )
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(_csv_con_filas(fila_con_error), encoding="utf-8")

    created, skipped = import_csv(db, str(csv_file))

    assert created == 0
    assert skipped == 1
    assert len(crud.list_piezas(db)) == 0


def test_import_csv_devuelve_conteos(db, tmp_path):
    """import_csv devuelve (created, skipped) como tupla de enteros."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(_csv_con_filas(FILA_COMPLETA), encoding="utf-8")

    resultado = import_csv(db, str(csv_file))

    assert isinstance(resultado, tuple)
    assert len(resultado) == 2
    created, skipped = resultado
    assert isinstance(created, int)
    assert isinstance(skipped, int)
