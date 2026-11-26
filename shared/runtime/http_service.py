"""Interfaz HTTP del runtime (ver shared/runtime/HTTP.md).

Solo biblioteca estándar. Es una capa delgada: traduce HTTP al contrato y los
errores del runtime a códigos de estado; no contiene lógica de negocio.
"""
import json
import logging
import os
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from shared.data_access.errors import BackendUnavailable, DataAccessError, InvalidMetadata
from shared.data_access.ids import is_valid_id

from .engine import EN_COLA, EN_EJECUCION
from .errors import InvalidRequest, TaskConflict, TaskNotFound

log = logging.getLogger("shared.runtime.http")

ENV_HOST = "ORQ_HTTP_HOST"
ENV_PORT = "ORQ_HTTP_PORT"
ENV_MAX_BODY = "ORQ_HTTP_MAX_BODY"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_MAX_BODY = 1024 * 1024


class _HttpError(Exception):
    def __init__(self, status, code, message, headers=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers or {}


def _translate(exc):
    """(estado HTTP, código) de los errores conocidos; None si no se reconoce."""
    if isinstance(exc, (InvalidRequest, InvalidMetadata)):
        return 400, exc.code
    if isinstance(exc, TaskNotFound):
        return 404, exc.code
    if isinstance(exc, TaskConflict):
        return 409, exc.code
    if isinstance(exc, BackendUnavailable):
        return 503, exc.code
    if isinstance(exc, DataAccessError):
        return 500, exc.code
    return None


def _env_int(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError("la variable %s debe ser un entero" % name)


class _Handler(BaseHTTPRequestHandler):
    runtime = None          # los fija make_server
    max_body = DEFAULT_MAX_BODY
    timeout = 30            # segundos sin actividad antes de cerrar la conexión
    server_version = "orq-runtime"

    # ---- respuestas ----------------------------------------------------------

    def _send_json(self, status, payload, headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        """Errores del propio protocolo (petición mal formada, etc.), también en JSON."""
        self.close_connection = True
        self._send_json(int(code), {"error": {"code": "http_%d" % int(code),
                                              "message": message or "petición inválida"}})

    def log_message(self, fmt, *args):
        log.info("%s - %s", self.address_string(), fmt % args)

    # ---- métodos -------------------------------------------------------------

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def _dispatch(self, method):
        try:
            status, payload, headers = self._handle(method)
        except _HttpError as exc:
            status, headers = exc.status, exc.headers
            payload = {"error": {"code": exc.code, "message": exc.message}}
        except Exception as exc:
            translated = _translate(exc)
            if translated is None:
                log.exception("error inesperado atendiendo %s %s", method, self.path)
                status, payload = 500, {"error": {"code": "internal_error",
                                                  "message": "error interno del servicio"}}
            else:
                status = translated[0]
                payload = {"error": {"code": translated[1], "message": str(exc)}}
            headers = None
        self._send_json(status, payload, headers)

    # ---- rutas ---------------------------------------------------------------

    def _handle(self, method):
        parts = urlsplit(self.path)
        path = parts.path
        query = parse_qs(parts.query)

        if path == "/health":
            self._require(method, "GET")
            return 200, self.runtime.health(), None
        if path == "/capabilities":
            self._require(method, "GET")
            return 200, self.runtime.capabilities(), None
        if path == "/tasks":
            self._require(method, "POST")
            record = self.runtime.submit(self._read_json_body())
            status = 202 if record["status"] in (EN_COLA, EN_EJECUCION) else 200
            return status, record, {"Location": "/tasks/" + record["task_id"]}
        if path.startswith("/tasks/"):
            self._require(method, "GET")
            task_id = path[len("/tasks/"):]
            if not is_valid_id("task", task_id):
                raise _HttpError(400, "invalid_request", "task_id inválido")
            run_id = (query.get("run_id") or [None])[0]
            if run_id is not None and not is_valid_id("run", run_id):
                raise _HttpError(400, "invalid_request", "run_id inválido")
            return 200, self.runtime.get(task_id, run_id=run_id), None
        raise _HttpError(404, "not_found", "ruta desconocida")

    def _require(self, method, allowed):
        if method != allowed:
            raise _HttpError(405, "method_not_allowed",
                             "esta ruta admite solo %s" % allowed, {"Allow": allowed})

    def _read_json_body(self):
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type != "application/json":
            raise _HttpError(415, "unsupported_media_type", "el cuerpo debe ser application/json")
        if self.headers.get("Transfer-Encoding"):
            raise _HttpError(411, "length_required", "no se admite Transfer-Encoding; use Content-Length")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise _HttpError(411, "length_required", "falta Content-Length")
        try:
            length = int(raw_length)
        except ValueError:
            raise _HttpError(400, "invalid_request", "Content-Length inválido")
        if length < 0:
            raise _HttpError(400, "invalid_request", "Content-Length inválido")
        if length > self.max_body:
            self.close_connection = True
            raise _HttpError(413, "payload_too_large", "el cuerpo supera %d bytes" % self.max_body)
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise _HttpError(400, "invalid_request", "cuerpo incompleto")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise _HttpError(400, "invalid_json", "el cuerpo no es JSON válido")


class _Server(ThreadingHTTPServer):
    daemon_threads = True


def make_server(runtime, host=None, port=None, max_body=None):
    """Crea el servidor HTTP del runtime (sin arrancarlo).

    host, port y max_body: argumento, o variables ORQ_HTTP_HOST / ORQ_HTTP_PORT /
    ORQ_HTTP_MAX_BODY, o los valores por defecto (127.0.0.1, 8000, 1 MiB).
    """
    host = host or os.environ.get(ENV_HOST) or DEFAULT_HOST
    port = port if port is not None else _env_int(ENV_PORT, DEFAULT_PORT)
    max_body = max_body if max_body is not None else _env_int(ENV_MAX_BODY, DEFAULT_MAX_BODY)
    handler = type("Handler", (_Handler,), {"runtime": runtime, "max_body": max_body})
    return _Server((host, port), handler)


def serve(runtime, host=None, port=None, max_body=None):
    """Arranca el runtime y el servidor; bloquea hasta SIGINT o SIGTERM.

    Al parar: deja de aceptar peticiones, cancela las tareas en cola (siguen
    registradas como en_cola y se reencolan al arrancar de nuevo) y la tarea en
    ejecución sigue hasta terminar. Si el proceso es terminado a la fuerza,
    esa tarea queda como `interrupted` al volver a arrancar.
    """
    server = make_server(runtime, host=host, port=port, max_body=max_body)
    runtime.start()

    def _stop(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    if threading.current_thread() is threading.main_thread():
        for name in ("SIGINT", "SIGTERM"):
            try:
                signal.signal(getattr(signal, name), _stop)
            except (AttributeError, ValueError, OSError):
                pass
    log.info("servicio %s escuchando en %s:%s", runtime.component.name, *server.server_address[:2])
    try:
        server.serve_forever()
    finally:
        server.server_close()
        runtime.shutdown(wait=False, cancel_pending=True)
