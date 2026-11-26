"""Motor del cascarón de servicio (ver shared/runtime/README.md)."""
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from shared.data_access.errors import ArtifactNotFound, ConflictError, DataAccessError
from shared.data_access.ids import is_valid_id, is_valid_ref, utc_now_iso

from .errors import InvalidRequest, TaskConflict, TaskNotFound
from .spec import TaskContext, TaskFailure

log = logging.getLogger("shared.runtime")

EN_COLA = "en_cola"
EN_EJECUCION = "en_ejecucion"
EXITOSA = "exitosa"
FALLIDA = "fallida"
PARCIAL = "parcial"

SCHEMA_VERSION = "0"
_REQUEST_KEYS = ("run_id", "task_id", "task", "inputs", "params", "retry_of")
_OUTPUT_KEYS = frozenset(
    ["source_dir", "status", "status_reason", "log_name", "scenario", "rule",
     "variant", "depends_on", "attributes"]
)
_MAX_PROGRESS = 50


def _error(code, message, stage, retryable=False):
    return {"code": code, "message": message, "stage": stage, "retryable": bool(retryable)}


def _kind_name(kind):
    if kind is None:
        return None
    kinds = kind if isinstance(kind, tuple) else (kind,)
    return "|".join(k.__name__ for k in kinds)


def _kind_ok(value, kind):
    if kind is None:
        return True
    kinds = kind if isinstance(kind, tuple) else (kind,)
    if isinstance(value, bool) and bool not in kinds:
        return False
    if isinstance(value, int) and not isinstance(value, bool) and float in kinds:
        return True
    return isinstance(value, kinds)


def _has_files(path):
    return path is not None and any(files for _d, _s, files in os.walk(str(path)))


def _normalize_request(request):
    if not isinstance(request, dict):
        raise InvalidRequest("la solicitud debe ser un objeto")
    unknown = [str(key) for key in request if key not in _REQUEST_KEYS]
    if unknown:
        raise InvalidRequest("campos desconocidos: " + ", ".join(sorted(unknown)))
    if not is_valid_id("run", request.get("run_id")):
        raise InvalidRequest("run_id inválido")
    if not is_valid_id("task", request.get("task_id")):
        raise InvalidRequest("task_id inválido")
    if not isinstance(request.get("task"), str) or not request["task"]:
        raise InvalidRequest("task es obligatorio")
    inputs = request.get("inputs", {})
    params = request.get("params", {})
    if not isinstance(inputs, dict) or not isinstance(params, dict):
        raise InvalidRequest("inputs y params deben ser objetos")
    clean = {
        "run_id": request["run_id"], "task_id": request["task_id"],
        "task": request["task"], "inputs": inputs, "params": params,
    }
    if request.get("retry_of") is not None:
        clean["retry_of"] = request["retry_of"]
    try:
        return json.loads(json.dumps(clean))  # canónica y serializable
    except (TypeError, ValueError) as exc:
        raise InvalidRequest("la solicitud debe ser serializable a JSON") from exc


class Runtime(object):
    """Recibe tareas, las valida, las ejecuta (con límite de concurrencia) y las registra."""

    def __init__(self, component, store):
        self._component = component
        self._store = store
        self._tasks = component.tasks
        self._executor = None
        self._lock = threading.Lock()
        self._pending = 0
        self._running = 0

    # ---- ciclo de vida -------------------------------------------------------

    def start(self):
        """Arranca los trabajadores y recupera las tareas que quedaron a medias."""
        if self._executor is not None:
            return
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(self._component.max_concurrent)),
            thread_name_prefix="runtime-" + self._component.name,
        )
        self._recover()

    def shutdown(self, wait=True, cancel_pending=False):
        """Detiene los trabajadores. Con cancel_pending, las tareas en cola no se
        ejecutan: quedan registradas como en_cola y se reencolan al arrancar de nuevo."""
        if self._executor is not None:
            self._executor.shutdown(wait=wait, cancel_futures=cancel_pending)

    def _recover(self):
        mine = self._store.listar_tareas(
            component=self._component.name, states=[EN_COLA, EN_EJECUCION]
        )
        for record in mine:
            if record["status"] == EN_EJECUCION:
                record["status"] = FALLIDA
                record["error"] = _error(
                    "interrupted", "el servicio se reinició mientras la tarea se ejecutaba",
                    "ejecucion", True,
                )
                record["finished_at"] = utc_now_iso()
                self._save(record)
        for record in mine:
            if record["status"] == EN_COLA:
                self._enqueue(record["run_id"], record["task_id"])

    # ---- API pública ---------------------------------------------------------

    def submit(self, request):
        """Registra la tarea y devuelve su registro (en_cola, o fallida si no pasa la validación)."""
        self.start()
        request = _normalize_request(request)
        existing = self._store.leer_tarea(request["task_id"])
        if existing is not None:
            return self._same_or_conflict(existing, request)

        task, effective, problems = self._check_request(request)
        record = self._new_record(request, effective)
        if problems:
            record["status"] = FALLIDA
            record["error"] = _error(
                problems[0][0], "; ".join(msg for _c, msg in problems), "validacion", False
            )
            record["finished_at"] = utc_now_iso()
            record["duration_seconds"] = 0.0
        try:
            self._store.crear_tarea(request["run_id"], request["task_id"], record)
        except ConflictError:  # otra solicitud idéntica llegó a la vez
            existing = self._store.leer_tarea(request["task_id"])
            return self._same_or_conflict(existing, request)
        if not problems:
            self._enqueue(request["run_id"], request["task_id"])
        return record

    def get(self, task_id, run_id=None):
        record = self._store.leer_tarea(task_id, run_id=run_id)
        if record is None:
            raise TaskNotFound("no existe la tarea %s" % task_id)
        return record

    def capabilities(self):
        tasks = {}
        for name, task in self._tasks.items():
            tasks[self._component.name + "." + name] = {
                "description": task.description,
                "inputs": dict(
                    (n, {"type": s.type, "required": s.required, "allow_partial": s.allow_partial})
                    for n, s in task.inputs.items()
                ),
                "params": dict(
                    (n, {"kind": _kind_name(s.kind), "default": s.default, "required": s.required,
                         "choices": s.choices, "description": s.description})
                    for n, s in task.params.items()
                ),
                "outputs": dict(
                    (n, {"type": s.type, "required": s.required,
                         "required_files": list(s.required_files)})
                    for n, s in task.outputs.items()
                ),
            }
        return {
            "component": self._component.name,
            "contract_version": self._component.contract_version,
            "max_concurrent": self._component.max_concurrent,
            "tasks": tasks,
        }

    def health(self):
        with self._lock:
            queued, running = self._pending, self._running
        return {
            "component": self._component.name, "status": "ok",
            "queued": queued, "running": running,
            "max_concurrent": self._component.max_concurrent,
        }

    # ---- registro y validación ----------------------------------------------

    def _same_or_conflict(self, existing, request):
        if existing["run_id"] != request["run_id"]:
            raise TaskConflict("el task_id ya existe en otra corrida")
        if existing["request"] != request:
            raise TaskConflict("el task_id ya existe con una solicitud distinta")
        return existing

    def _new_record(self, request, effective):
        return {
            "schema_version": SCHEMA_VERSION,
            "task_id": request["task_id"],
            "run_id": request["run_id"],
            "component": self._component.name,
            "task": request["task"],
            "request": request,
            "effective_params": effective,
            "status": EN_COLA,
            "outputs": {},
            "error": None,
            "warnings": [],
            "progress": [],
            "created_at": utc_now_iso(),
            "started_at": None,
            "finished_at": None,
            "duration_seconds": None,
        }

    def _check_request(self, request):
        """Validación estructural. Devuelve (tarea, parámetros efectivos, problemas)."""
        problems = []
        prefix = self._component.name + "."
        name = request["task"]
        if not name.startswith(prefix) or name[len(prefix):] not in self._tasks:
            return None, {}, [(
                "unknown_task",
                "este servicio atiende solo: " + ", ".join(sorted(prefix + t for t in self._tasks)),
            )]
        task = self._tasks[name[len(prefix):]]

        for input_name in sorted(request["inputs"]):
            if input_name not in task.inputs:
                problems.append(("unknown_input", "entrada no declarada: %s" % input_name))
        for input_name, spec in task.inputs.items():
            if input_name not in request["inputs"]:
                if spec.required:
                    problems.append(("missing_input", "falta la entrada %s" % input_name))
                continue
            ref = request["inputs"][input_name]
            if not is_valid_ref(ref):
                problems.append(("invalid_input", "la entrada %s no es una referencia válida" % input_name))
                continue
            try:
                meta = self._store.leer_metadatos(ref)
            except ArtifactNotFound:
                problems.append(("input_not_found", "la entrada %s no existe" % input_name))
                continue
            except DataAccessError as exc:
                problems.append(("input_unavailable", "la entrada %s no se pudo leer (%s)" % (input_name, exc.code)))
                continue
            if meta.get("type") != spec.type:
                problems.append((
                    "wrong_input_type",
                    "la entrada %s espera %s y recibió %s" % (input_name, spec.type, meta.get("type")),
                ))
            elif meta.get("status") != "completo" and not (spec.allow_partial and meta.get("status") == "parcial"):
                problems.append((
                    "input_not_ready",
                    "la entrada %s está en estado %s" % (input_name, meta.get("status")),
                ))

        effective = {}
        for param in sorted(request["params"]):
            if param not in task.params:
                problems.append(("unknown_param", "parámetro no declarado: %s" % param))
        for param, spec in task.params.items():
            if param in request["params"]:
                value = request["params"][param]
            elif spec.required:
                problems.append(("missing_param", "falta el parámetro %s" % param))
                continue
            else:
                value = spec.default
            if value is not None and not _kind_ok(value, spec.kind):
                problems.append(("invalid_param", "el parámetro %s debe ser de tipo %s" % (param, _kind_name(spec.kind))))
            elif spec.choices is not None and value not in spec.choices:
                problems.append(("invalid_param", "el parámetro %s debe ser uno de %s" % (param, spec.choices)))
            effective[param] = value

        retry = request.get("retry_of")
        if retry is not None:
            previous = self._store.leer_tarea(retry) if is_valid_id("task", retry) else None
            if previous is None or previous["run_id"] != request["run_id"]:
                problems.append(("invalid_retry_of", "retry_of debe ser una tarea existente de la misma corrida"))
        return task, effective, problems

    # ---- ejecución -----------------------------------------------------------

    def _enqueue(self, run_id, task_id):
        with self._lock:
            self._pending += 1
        self._executor.submit(self._execute, run_id, task_id)

    def _save(self, record):
        try:
            self._store.actualizar_tarea(record)
        except DataAccessError:
            log.exception("no se pudo guardar el estado de %s", record.get("task_id"))

    def _report(self, record, message):
        record["progress"].append({"at": utc_now_iso(), "message": message[:500]})
        del record["progress"][:-_MAX_PROGRESS]
        self._save(record)

    def _execute(self, run_id, task_id):
        with self._lock:
            self._pending -= 1
            self._running += 1
        started = time.monotonic()
        record = None
        keep_work = True
        try:
            record = self._store.leer_tarea(task_id, run_id=run_id)
            if record is None:
                return
            record["status"] = EN_EJECUCION
            record["started_at"] = utc_now_iso()
            self._save(record)
            status, error, outputs, warnings, keep_work = self._process(record)
        except Exception:
            log.exception("error interno en la tarea %s", task_id)
            status, error, outputs, warnings = FALLIDA, _error(
                "internal_error", "error interno del servicio", "interno", False), {}, []
        finally:
            with self._lock:
                self._running -= 1
        if record is None:
            return
        record["status"] = status
        record["error"] = error
        record["outputs"] = outputs
        record["warnings"] = list(record["warnings"]) + warnings
        record["finished_at"] = utc_now_iso()
        record["duration_seconds"] = round(time.monotonic() - started, 3)
        self._save(record)
        if not keep_work:
            try:
                self._store.eliminar_trabajo(run_id, task_id)
            except DataAccessError:
                log.exception("no se pudo borrar la carpeta de trabajo de %s", task_id)

    def _process(self, record):
        """Devuelve (estado, error, salidas, avisos, conservar_carpeta_de_trabajo)."""
        run_id, task_id = record["run_id"], record["task_id"]
        task = self._tasks[record["task"].split(".", 1)[1]]

        # 1. Entradas
        try:
            work_dir = self._store.carpeta_trabajo(run_id, task_id)
            inputs = {}
            for name, ref in record["request"]["inputs"].items():
                got = self._store.obtener(ref, task_id, run_id=run_id)
                inputs[name] = {"ref": ref, "path": got["path"], "metadata": got["metadata"]}
        except DataAccessError as exc:
            return FALLIDA, _error(exc.code, str(exc), "entradas", exc.code == "backend_unavailable"), {}, [], True
        ctx = TaskContext(run_id, task_id, record["task"], inputs, record["effective_params"],
                          work_dir, lambda message: self._report(record, message))

        # 2. Precondiciones de contenido (antes de ejecutar nada)
        if task.preconditions is not None:
            try:
                problems = list(task.preconditions(ctx) or [])
            except Exception:
                log.exception("error en las precondiciones de %s", task_id)
                return FALLIDA, _error("precondition_error", "no se pudieron comprobar las precondiciones", "precondiciones"), {}, [], True
            if problems:
                return FALLIDA, _error("precondition_failed", "; ".join(problems), "precondiciones"), {}, [], True

        # 3. Ejecución
        failure, returned = None, {}
        try:
            returned = task.execute(ctx) or {}
            if not isinstance(returned, dict):
                raise TypeError("execute debe devolver un diccionario de salidas")
        except TaskFailure as exc:
            failure = _error(exc.code, exc.message, "ejecucion", exc.retryable)
            returned = exc.outputs or {}
        except Exception as exc:
            log.exception("la tarea %s falló", task_id)
            failure = _error("execution_error", "%s: %s" % (exc.__class__.__name__, exc), "ejecucion", False)
            returned = {}
        if failure is not None:
            failure["message"] = failure["message"].replace(work_dir, "<trabajo>")

        # 4. Verificar y registrar las salidas (el código de retorno no basta)
        refs, fatal, warnings, partial = self._register(ctx, task, returned, failure)

        if failure is not None:
            return FALLIDA, failure, refs, warnings, True
        if fatal:
            return FALLIDA, _error(fatal[0][0], "; ".join(msg for _c, msg in fatal), "salidas"), refs, warnings, True
        return (PARCIAL if partial else EXITOSA), None, refs, warnings, False

    def _register(self, ctx, task, returned, failure):
        refs, fatal, warnings, partial = {}, [], [], False
        default_depends = []
        for entry in ctx.inputs.values():
            if entry["ref"] not in default_depends:
                default_depends.append(entry["ref"])

        for name in sorted(returned):
            if name not in task.outputs:
                fatal.append(("invalid_output", "salida no declarada: %s" % name))

        for name, spec in task.outputs.items():
            if name not in returned:
                if spec.required and failure is None:
                    fatal.append(("missing_output", "falta la salida declarada %s" % name))
                continue
            result = returned[name] or {}
            bad = sorted(str(key) for key in result if key not in _OUTPUT_KEYS)
            if bad:
                fatal.append(("invalid_output", "la salida %s trae campos no permitidos: %s" % (name, ", ".join(bad))))
                continue

            source = result.get("source_dir")
            if source is None:
                default = Path(ctx.work_dir) / "out" / name
                source = str(default) if default.is_dir() else None
            source_ok = source is not None and Path(source).is_dir()
            has_files = source_ok and _has_files(source)
            declared = result.get("status", "completo")
            reason = result.get("status_reason")
            if declared not in ("completo", "parcial", "fallido"):
                fatal.append(("invalid_output", "la salida %s trae un estado inválido" % name))
                continue

            problems = []
            if declared == "fallido":
                problems.append(reason or "el componente la declaró fallida")
            if declared == "completo" and not has_files:
                problems.append("la carpeta de salida no existe o está vacía")
            for pattern in spec.required_files:
                if not (source_ok and any(p.is_file() for p in Path(source).glob(pattern))):
                    problems.append("falta un archivo que cumpla %s" % pattern)

            if problems:
                status = "fallido" if declared == "fallido" or not has_files else "parcial"
                reason = "; ".join(problems)
            elif failure is not None and declared == "completo":
                status, reason = "parcial", "la tarea terminó fallida (%s)" % failure["code"]
            elif declared == "parcial":
                status, reason = "parcial", reason or "el componente la declaró parcial"
                partial = True
            else:
                status, reason = "completo", None

            kwargs = {}
            for key in ("log_name", "scenario", "rule", "variant", "attributes"):
                if result.get(key) is not None:
                    kwargs[key] = result[key]
            try:
                ref = self._store.guardar(
                    run_id=ctx.run_id, producer=self._component.name, task_id=ctx.task_id,
                    type=spec.type, status=status, status_reason=reason,
                    source_dir=source if has_files else None,
                    depends_on=result["depends_on"] if "depends_on" in result else default_depends,
                    **kwargs
                )
            except DataAccessError as exc:
                fatal.append(("invalid_output", "no se pudo registrar la salida %s: %s" % (name, exc)))
                continue
            refs[name] = ref

            if problems:
                if spec.required:
                    fatal.append(("missing_output", "la salida %s no es utilizable: %s" % (name, reason)))
                else:
                    warnings.append("la salida opcional %s quedó %s: %s" % (name, status, reason))
        return refs, fatal, warnings, partial

    @property
    def component(self):
        return self._component
