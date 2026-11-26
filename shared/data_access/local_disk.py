"""Respaldo de disco local (ver shared/data_access/README.md).

Disposición:
    <raíz>/<run_id>/artifacts/<artifact_id>/{data/, metadata.json}
    <raíz>/<run_id>/work/<task_id>/{in/, out/}
    <raíz>/<run_id>/tasks/   (reservado)

Un artefacto sin metadata.json no existe: los bytes se guardan primero y el
metadato se publica al final con un renombrado atómico.
"""
import json
import os
import secrets
import shutil
from pathlib import Path

from .errors import (
    ArtifactNotFound, BackendUnavailable, ConflictError, IntegrityError, InvalidMetadata,
)
from .ids import is_valid_id, is_valid_ref, new_id, utc_now_iso
from .interface import ArtifactStore
from .inventory import build_inventory, compare_inventory
from .validation import ensure_valid, load_registry

ENV_ROOT = "ORQ_STORE_PATH"
DEFAULT_ROOT = "local_store"


class LocalDiskStore(ArtifactStore):
    """Raíz del almacén: argumento, o variable ORQ_STORE_PATH, o ./local_store."""

    def __init__(self, root=None, registry_path=None):
        chosen = root or os.environ.get(ENV_ROOT) or DEFAULT_ROOT
        self._root = Path(chosen).expanduser().resolve()
        self._registry = load_registry(registry_path)

    # ---- métodos internos -------------------------------------------------

    def _require_id(self, kind, value):
        if not is_valid_id(kind, value):
            raise InvalidMetadata(["identificador inválido (%s)" % kind])

    def _check_ref(self, ref):
        if not is_valid_ref(ref):
            raise InvalidMetadata(
                ["referencia inválida: debe ser {run_id, artifact_id} con identificadores válidos"]
            )

    def _artifact_dir(self, ref):
        return self._root / ref["run_id"] / "artifacts" / ref["artifact_id"]

    def _ref_exists(self, ref):
        return (self._artifact_dir(ref) / "metadata.json").is_file()

    def _work_dir(self, run_id, task_id):
        return self._root / run_id / "work" / task_id

    def _read_json(self, path, artifact_id):
        try:
            with open(str(path), encoding="utf-8") as handle:
                return json.load(handle)
        except ValueError as exc:
            raise IntegrityError(f"metadato ilegible en {artifact_id}", [artifact_id]) from exc
        except OSError as exc:
            raise BackendUnavailable(f"no se pudo leer el metadato: {exc.__class__.__name__}") from exc

    def _write_tmp(self, path, data):
        tmp = path.with_name(path.name + ".tmp-" + secrets.token_hex(4))
        with open(str(tmp), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return tmp

    def _discard_tmp(self, tmp):
        try:
            if tmp is not None and tmp.exists():
                tmp.unlink()
        except OSError:
            pass

    def _write_json_atomic(self, path, data):
        tmp = None
        try:
            tmp = self._write_tmp(path, data)
            os.replace(str(tmp), str(path))
        finally:
            self._discard_tmp(tmp)

    # ---- operaciones ---------------------------------------------------------

    def guardar(self, *, run_id, producer, type, status, source_dir=None,
                task_id=None, status_reason=None, log_name=None, scenario=None,
                rule=None, variant=None, depends_on=None, attributes=None):
        self._require_id("run", run_id)
        artifact_id = new_id("art")
        meta = {
            "schema_version": self._registry["schema_version"],
            "artifact_id": artifact_id,
            "run_id": run_id,
            "producer": producer,
            "type": type,
            "status": status,
            "created_at": utc_now_iso(),
            "depends_on": list(depends_on) if depends_on else [],
            "files": [],
        }
        optional = (
            ("task_id", task_id), ("status_reason", status_reason), ("log_name", log_name),
            ("scenario", scenario), ("rule", rule), ("variant", variant),
            ("attributes", attributes),
        )
        for key, value in optional:
            if value is not None:
                meta[key] = value

        # Validación previa, antes de copiar nada (aún sin exigir archivos).
        ensure_valid(meta, self._registry, exists=self._ref_exists, check_files=False)
        if source_dir is not None and not Path(source_dir).is_dir():
            raise InvalidMetadata(["la carpeta de origen no existe o no es una carpeta"])

        art_dir = self._root / run_id / "artifacts" / artifact_id
        try:
            art_dir.parent.mkdir(parents=True, exist_ok=True)
            art_dir.mkdir()
        except FileExistsError as exc:
            raise ConflictError("el artefacto %s ya existe" % artifact_id) from exc
        except OSError as exc:
            raise BackendUnavailable("no se pudo crear el artefacto: %s" % exc.__class__.__name__) from exc

        try:
            data_dir = art_dir / "data"
            if source_dir is None:
                data_dir.mkdir()
            else:
                shutil.copytree(str(source_dir), str(data_dir))
            meta["files"] = build_inventory(data_dir)  # sobre lo copiado, no sobre el origen
            ensure_valid(meta, self._registry)
            self._write_json_atomic(art_dir / "metadata.json", meta)
        except OSError as exc:
            shutil.rmtree(str(art_dir), ignore_errors=True)
            raise BackendUnavailable("no se pudo guardar el artefacto: %s" % exc.__class__.__name__) from exc
        except Exception:
            shutil.rmtree(str(art_dir), ignore_errors=True)
            raise
        return {"run_id": run_id, "artifact_id": artifact_id}

    def leer_metadatos(self, ref):
        self._check_ref(ref)
        path = self._artifact_dir(ref) / "metadata.json"
        if not path.is_file():
            raise ArtifactNotFound("no existe el artefacto %s" % ref["artifact_id"])
        return self._read_json(path, ref["artifact_id"])

    def listar(self, run_id, *, type=None, status=None, scenario=None, producer=None):
        self._require_id("run", run_id)
        base = self._root / run_id / "artifacts"
        if not base.is_dir():
            return []
        try:
            names = sorted(os.listdir(str(base)))
        except OSError as exc:
            raise BackendUnavailable("no se pudo listar: %s" % exc.__class__.__name__) from exc
        found = []
        for name in names:
            meta_path = base / name / "metadata.json"
            if not is_valid_id("art", name) or not meta_path.is_file():
                continue  # huérfano o basura: se ignora
            meta = self._read_json(meta_path, name)
            if type is not None and meta.get("type") != type:
                continue
            if status is not None and meta.get("status") != status:
                continue
            if scenario is not None and meta.get("scenario") != scenario:
                continue
            if producer is not None and meta.get("producer") != producer:
                continue
            found.append(meta)
        found.sort(key=lambda m: (m.get("created_at", ""), m.get("artifact_id", "")))
        return found

    def obtener(self, ref, task_id, *, run_id=None, verificar=True):
        self._check_ref(ref)
        self._require_id("task", task_id)
        task_run = run_id or ref["run_id"]
        self._require_id("run", task_run)
        meta = self.leer_metadatos(ref)

        data_dir = self._artifact_dir(ref) / "data"
        dest = self._work_dir(task_run, task_id) / "in" / ref["artifact_id"]
        try:
            if dest.exists():
                shutil.rmtree(str(dest))
            dest.parent.mkdir(parents=True, exist_ok=True)
            if data_dir.is_dir():
                shutil.copytree(str(data_dir), str(dest))
            elif meta.get("files"):
                raise IntegrityError(
                    "faltan los datos del artefacto %s" % ref["artifact_id"],
                    [entry["path"] for entry in meta["files"]],
                )
            else:
                dest.mkdir()
        except OSError as exc:
            raise BackendUnavailable("no se pudo materializar el artefacto: %s" % exc.__class__.__name__) from exc

        if verificar:
            problems = compare_inventory(meta.get("files", []), build_inventory(dest))
            if problems:
                shutil.rmtree(str(dest), ignore_errors=True)
                raise IntegrityError(
                    "el artefacto %s no coincide con su inventario" % ref["artifact_id"], problems
                )
        return {"path": str(dest), "metadata": meta}

    def cambiar_estado(self, ref, status, status_reason=None):
        meta = self.leer_metadatos(ref)
        meta["status"] = status
        if status_reason is None:
            meta.pop("status_reason", None)
        else:
            meta["status_reason"] = status_reason
        ensure_valid(meta, self._registry)
        try:
            self._write_json_atomic(self._artifact_dir(ref) / "metadata.json", meta)
        except OSError as exc:
            raise BackendUnavailable("no se pudo actualizar el estado: %s" % exc.__class__.__name__) from exc
        return meta

    # ---- carpeta de trabajo de la tarea (utilidades del respaldo local) -------

    def carpeta_trabajo(self, run_id, task_id):
        """Crea work/<task_id>/{in,out} y devuelve la ruta de la carpeta de trabajo."""
        self._require_id("run", run_id)
        self._require_id("task", task_id)
        work = self._work_dir(run_id, task_id)
        try:
            (work / "in").mkdir(parents=True, exist_ok=True)
            (work / "out").mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise BackendUnavailable("no se pudo crear la carpeta de trabajo: %s" % exc.__class__.__name__) from exc
        return str(work)

    def eliminar_trabajo(self, run_id, task_id):
        """Borra work/<task_id>/. La política (borrar si termina bien, conservar si falla) la aplica el runtime."""
        self._require_id("run", run_id)
        self._require_id("task", task_id)
        work = self._work_dir(run_id, task_id)
        try:
            if work.exists():
                shutil.rmtree(str(work))
        except OSError as exc:
            raise BackendUnavailable("no se pudo borrar la carpeta de trabajo: %s" % exc.__class__.__name__) from exc

    # ---- registro de tareas ---------------------------------------------------

    def _task_path(self, run_id, task_id):
        return self._root / run_id / "tasks" / (task_id + ".json")

    def crear_tarea(self, run_id, task_id, record):
        self._require_id("run", run_id)
        self._require_id("task", task_id)
        path = self._task_path(run_id, task_id)
        tmp = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._write_tmp(path, record)
            os.link(str(tmp), str(path))  # falla si ya existe: creación exclusiva y atómica
        except FileExistsError as exc:
            raise ConflictError("la tarea %s ya existe" % task_id) from exc
        except OSError as exc:
            raise BackendUnavailable("no se pudo crear la tarea: %s" % exc.__class__.__name__) from exc
        finally:
            self._discard_tmp(tmp)

    def leer_tarea(self, task_id, run_id=None):
        self._require_id("task", task_id)
        if run_id is not None:
            self._require_id("run", run_id)
            candidates = [run_id]
        else:
            try:
                names = sorted(os.listdir(str(self._root))) if self._root.is_dir() else []
            except OSError as exc:
                raise BackendUnavailable("no se pudo listar: %s" % exc.__class__.__name__) from exc
            candidates = [name for name in names if is_valid_id("run", name)]
        for candidate in candidates:
            path = self._task_path(candidate, task_id)
            if path.is_file():
                return self._read_json(path, task_id)
        return None

    def actualizar_tarea(self, record):
        run_id, task_id = record.get("run_id"), record.get("task_id")
        self._require_id("run", run_id)
        self._require_id("task", task_id)
        path = self._task_path(run_id, task_id)
        if not path.is_file():
            raise ArtifactNotFound("no existe la tarea %s" % task_id)
        try:
            self._write_json_atomic(path, record)
        except OSError as exc:
            raise BackendUnavailable("no se pudo actualizar la tarea: %s" % exc.__class__.__name__) from exc

    def listar_tareas(self, run_id=None, *, component=None, states=None):
        if run_id is not None:
            self._require_id("run", run_id)
            runs = [run_id]
        else:
            try:
                names = sorted(os.listdir(str(self._root))) if self._root.is_dir() else []
            except OSError as exc:
                raise BackendUnavailable("no se pudo listar: %s" % exc.__class__.__name__) from exc
            runs = [name for name in names if is_valid_id("run", name)]
        found = []
        for run in runs:
            base = self._root / run / "tasks"
            if not base.is_dir():
                continue
            for name in sorted(os.listdir(str(base))):
                if not name.endswith(".json") or not is_valid_id("task", name[:-5]):
                    continue
                record = self._read_json(base / name, name[:-5])
                if component is not None and record.get("component") != component:
                    continue
                if states is not None and record.get("status") not in states:
                    continue
                found.append(record)
        found.sort(key=lambda r: (r.get("created_at", ""), r.get("task_id", "")))
        return found
