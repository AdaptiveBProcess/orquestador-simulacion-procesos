"""Ejecución de herramientas externas como subproceso, con tiempo límite.

Lo usan los componentes que envuelven un programa (Prosimos, BIMP...). Termina
todo el grupo de procesos si se supera el tiempo límite. Solo biblioteca estándar.
"""
import os
import shlex
import shutil
import signal
import subprocess
import time
from pathlib import Path


class ProcessResult(object):
    def __init__(self, returncode, timed_out, log_path):
        self.returncode = returncode
        self.timed_out = timed_out
        self.log_path = log_path


def command_available(command):
    """True si el primer elemento del comando existe en el PATH."""
    parts = shlex.split(command)
    return bool(parts) and shutil.which(parts[0]) is not None


def run_process(argv, cwd, log_path, timeout, on_tick=None, tick_every=30.0, poll=0.5):
    """Ejecuta `argv` con `cwd`, guardando salida y errores en `log_path`.

    `on_tick(segundos)` se llama cada `tick_every` segundos mientras corre.
    Si pasan más de `timeout` segundos, termina el grupo de procesos y marca timed_out.
    """
    extra = {"start_new_session": True} if os.name == "posix" else {}
    started = time.monotonic()
    last_tick = started
    timed_out = False
    with open(str(log_path), "wb") as log:
        process = subprocess.Popen(argv, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT, **extra)
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
    return ProcessResult(process.returncode, timed_out, Path(log_path))


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
    """Final de la salida de un proceso, para incluirlo en un mensaje de error."""
    try:
        text = Path(log_path).read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.strip().splitlines()[-lines:])[-max_chars:]
