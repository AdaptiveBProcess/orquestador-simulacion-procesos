"""Ejecución de Simod como subproceso y localización de sus resultados."""
import os
import shlex
import signal
import subprocess
import time
from pathlib import Path


class SimodResult(object):
    def __init__(self, returncode, timed_out, log_path):
        self.returncode = returncode
        self.timed_out = timed_out
        self.log_path = log_path


def command_available(command):
    """Comprueba que el primer elemento del comando existe en el PATH."""
    import shutil
    parts = shlex.split(command)
    return bool(parts) and shutil.which(parts[0]) is not None


def run_simod(command, home, config_path, output_dir, log_path, timeout,
              on_tick=None, tick_every=30.0, poll=0.5):
    """Ejecuta `<command> --configuration <config> --output <dir>` con `home` como cwd.

    Devuelve un SimodResult. Si se supera `timeout` segundos, termina el grupo de procesos.
    """
    argv = shlex.split(command) + ["--configuration", str(config_path), "--output", str(output_dir)]
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    extra = {"start_new_session": True} if os.name == "posix" else {}
    started = time.monotonic()
    last_tick = started
    timed_out = False
    with open(str(log_path), "wb") as log:
        process = subprocess.Popen(argv, cwd=str(home), stdout=log, stderr=subprocess.STDOUT, **extra)
        while process.poll() is None:
            now = time.monotonic()
            if now - started > timeout:
                timed_out = True
                _terminate(process)
                break
            if on_tick is not None and now - last_tick >= tick_every:
                on_tick(int(now - started))
                last_tick = now
            time.sleep(poll)
    return SimodResult(process.returncode, timed_out, Path(log_path))


def _terminate(process):
    for sig, wait in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        try:
            if hasattr(os, "killpg"):
                os.killpg(process.pid, sig)
            else:
                process.kill()
        except (ProcessLookupError, PermissionError):
            return
        try:
            process.wait(timeout=wait)
            return
        except subprocess.TimeoutExpired:
            continue


def log_tail(log_path, lines=15, max_chars=1500):
    try:
        text = Path(log_path).read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""
    tail = "\n".join(text.strip().splitlines()[-lines:])
    return tail[-max_chars:]


def locate_results(output_dir):
    """(carpeta best_result o None, carpeta de la corrida de Simod o None)."""
    base = Path(output_dir)
    if (base / "best_result").is_dir():
        return base / "best_result", base
    runs = sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []
    with_best = [p for p in runs if (p / "best_result").is_dir()]
    if with_best:
        return with_best[-1] / "best_result", with_best[-1]
    return None, (runs[-1] if runs else None)


def model_files(best_result):
    """(nombre del BPMN, nombre del JSON de recursos) si el resultado está completo; si no, None."""
    if best_result is None:
        return None
    bpmn = sorted(p for p in Path(best_result).glob("*.bpmn") if p.is_file())
    if len(bpmn) != 1:
        return None
    resources = Path(best_result) / (bpmn[0].stem + ".json")
    return (bpmn[0].name, resources.name) if resources.is_file() else None
