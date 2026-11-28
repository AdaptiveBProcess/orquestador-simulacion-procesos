"""Invocación de Prosimos y utilidades sobre sus archivos de salida."""
import os
import shlex
import shutil
from pathlib import Path

WARNINGS_FILE = "simulation_warnings.txt"


def build_argv(command, bpmn_path, json_path, total_cases, log_out, stats_out):
    """`<command> start-simulation ...`, con los mismos argumentos que usaba el código original."""
    return shlex.split(command) + [
        "start-simulation",
        "--bpmn_path", str(bpmn_path),
        "--json_path", str(json_path),
        "--total_cases", str(int(total_cases)),
        "--log_out_path", str(log_out),
        "--stat_out_path", str(stats_out),
    ]


def clear_stale_warnings(home):
    """Borra un archivo de avisos de una ejecución anterior que haya quedado en `home`."""
    try:
        (Path(home) / WARNINGS_FILE).unlink()
    except FileNotFoundError:
        pass


def collect_warnings(home, output_dir):
    """Si Prosimos dejó el archivo de avisos en `home`, lo mueve junto a las salidas. True si existe."""
    target = Path(output_dir) / WARNINGS_FILE
    stray = Path(home) / WARNINGS_FILE
    if stray.is_file() and not target.exists():
        shutil.move(str(stray), str(target))
    return target.is_file()


def has_content(path):
    """El archivo existe y no está vacío."""
    return os.path.isfile(str(path)) and os.path.getsize(str(path)) > 0
