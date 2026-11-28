"""Búsqueda, preparación y conteo de casos del log que se entrega a Simod."""
import csv
import gzip
import shutil
from pathlib import Path


class LogError(Exception):
    """El log recibido no se puede usar (ambiguo, sin la columna de caso, etc.)."""


def find_log_file(folder):
    """Devuelve el archivo de log de una carpeta, preferiendo `.csv.gz` sobre `.csv`."""
    base = Path(folder)
    for suffix in (".csv.gz", ".csv"):
        found = sorted(p for p in base.rglob("*" + suffix) if p.is_file())
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            raise LogError("hay varios archivos %s en el log: %s" % (suffix, ", ".join(p.name for p in found)))
    raise LogError("el log no contiene ningún archivo .csv.gz ni .csv")


def _open_text(path):
    if str(path).endswith(".gz"):
        return gzip.open(str(path), "rt", encoding="utf-8", newline="")
    return open(str(path), "r", encoding="utf-8", newline="")


def count_cases(path, case_column):
    """Número de casos distintos del log."""
    with _open_text(path) as handle:
        reader = csv.DictReader(handle)
        if case_column not in (reader.fieldnames or []):
            raise LogError("el log no tiene la columna de caso %r" % case_column)
        return len(set(row[case_column] for row in reader if row[case_column] != ""))


def prepare_gz(source, dest_dir):
    """Deja en `dest_dir` el log como `.csv.gz` (lo comprime si llegó como `.csv`)."""
    source = Path(source)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    if source.name.endswith(".csv.gz"):
        target = dest_dir / source.name
        shutil.copyfile(str(source), str(target))
    else:
        target = dest_dir / (source.stem + ".csv.gz")
        with open(str(source), "rb") as raw, gzip.open(str(target), "wb") as packed:
            shutil.copyfileobj(raw, packed)
    return target
