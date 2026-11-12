# Pruebas del escáner de archivos musicales
import os
from pathlib import Path

import pytest

from app.scanner import ScanCandidate, parse_filename, scan_folder


def test_parse_filename_composer_title():
    """'Bach - Suite No.1' → title='Suite No.1', composer='Bach'"""
    title, composer = parse_filename("Bach - Suite No.1")
    assert title == "Suite No.1"
    assert composer == "Bach"


def test_parse_filename_title_only():
    """'Cielito_Lindo' → title='Cielito Lindo', composer=None"""
    title, composer = parse_filename("Cielito_Lindo")
    assert title == "Cielito Lindo"
    assert composer is None


def test_parse_filename_strips_leading_numbers():
    """'01 - La Bikina' → title='La Bikina' (el número inicial se elimina)"""
    title, _ = parse_filename("01 - La Bikina")
    assert title == "La Bikina"


def test_parse_filename_strips_leading_numbers_no_separator():
    """'02. La Llorona' → title='La Llorona'"""
    title, composer = parse_filename("02. La Llorona")
    assert title == "La Llorona"
    assert composer is None


def test_parse_filename_composer_title_with_number():
    """'03 - Mozart - Eine Kleine' → title='Eine Kleine', composer='Mozart'"""
    title, composer = parse_filename("03 - Mozart - Eine Kleine")
    assert title == "Eine Kleine"
    assert composer == "Mozart"


def test_parse_filename_underscores_to_spaces():
    """Los guiones bajos se convierten en espacios."""
    title, _ = parse_filename("La_Bikina_Vals")
    assert title == "La Bikina Vals"


def test_scan_folder_finds_music_files(tmp_path):
    """El escáner devuelve solo archivos con extensiones musicales."""
    (tmp_path / "Bach - Suite.pdf").write_bytes(b"")
    (tmp_path / "notas.txt").write_bytes(b"")
    (tmp_path / "imagen.jpg").write_bytes(b"")
    results = scan_folder(str(tmp_path))
    assert len(results) == 1
    assert results[0].format == "pdf"


def test_scan_folder_all_music_extensions(tmp_path):
    """Verifica que se detecten todas las extensiones musicales permitidas."""
    extensiones = [".pdf", ".mxl", ".musicxml", ".mscz", ".mscx", ".sib", ".musx", ".capx"]
    for ext in extensiones:
        (tmp_path / f"pieza{ext}").write_bytes(b"")
    results = scan_folder(str(tmp_path))
    assert len(results) == len(extensiones)


def test_scan_folder_returns_scan_candidates(tmp_path):
    """Los resultados son instancias de ScanCandidate con los campos correctos."""
    (tmp_path / "Bach - Preludio.pdf").write_bytes(b"")
    results = scan_folder(str(tmp_path))
    assert len(results) == 1
    candidate = results[0]
    assert isinstance(candidate, ScanCandidate)
    assert candidate.format == "pdf"
    assert candidate.inferred_title == "Preludio"
    assert candidate.inferred_composer == "Bach"
    assert candidate.location_type in ("mac", "icloud")


def test_scan_folder_recursive(tmp_path):
    """El escáner es recursivo y encuentra archivos en subdirectorios."""
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "pieza.mscz").write_bytes(b"")
    results = scan_folder(str(tmp_path))
    assert len(results) == 1


def test_scan_folder_detects_icloud_path():
    """Un ScanCandidate con ruta de iCloud debe tener location_type='icloud'."""
    icloud_root = str(Path.home() / "Library/Mobile Documents/com~apple~CloudDocs")
    candidate = ScanCandidate(
        path=f"{icloud_root}/piece.mscz",
        inferred_title="piece",
        inferred_composer=None,
        format="mscz",
        location_type="icloud",
    )
    assert candidate.location_type == "icloud"


def test_scan_folder_detects_mac_path(tmp_path):
    """Un archivo en una ruta local normal debe tener location_type='mac'."""
    (tmp_path / "pieza.pdf").write_bytes(b"")
    results = scan_folder(str(tmp_path))
    assert results[0].location_type == "mac"


def test_scan_folder_empty_dir(tmp_path):
    """Un directorio vacío devuelve lista vacía."""
    results = scan_folder(str(tmp_path))
    assert results == []


def test_scan_folder_case_insensitive_extension(tmp_path):
    """Las extensiones en mayúsculas también deben detectarse."""
    (tmp_path / "Pieza.PDF").write_bytes(b"")
    results = scan_folder(str(tmp_path))
    assert len(results) == 1
    assert results[0].format == "pdf"
