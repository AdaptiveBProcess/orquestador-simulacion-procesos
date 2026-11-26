"""Inventario de archivos de una carpeta: ruta relativa, tamaño y sha256."""
import hashlib
import os
from pathlib import Path

_CHUNK = 1024 * 1024


def file_sha256(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_inventory(folder):
    """Lista de {path, size_bytes, sha256}; rutas relativas con '/', ordenadas."""
    base = Path(folder)
    entries = []
    for dirpath, dirnames, filenames in os.walk(str(base)):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            entries.append(
                {
                    "path": full.relative_to(base).as_posix(),
                    "size_bytes": full.stat().st_size,
                    "sha256": file_sha256(full),
                }
            )
    entries.sort(key=lambda entry: entry["path"])
    return entries


def compare_inventory(expected, actual):
    """Devuelve las diferencias ('falta', 'distinto', 'sobra'); vacía si coinciden."""
    wanted = dict((entry["path"], entry) for entry in expected)
    found = dict((entry["path"], entry) for entry in actual)
    problems = []
    for path in sorted(wanted):
        if path not in found:
            problems.append("falta: " + path)
        elif (
            found[path]["sha256"] != wanted[path]["sha256"]
            or found[path]["size_bytes"] != wanted[path]["size_bytes"]
        ):
            problems.append("distinto: " + path)
    for path in sorted(found):
        if path not in wanted:
            problems.append("sobra: " + path)
    return problems
