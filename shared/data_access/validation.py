"""Validación de metadatos (ver shared/contracts/artifact-metadata.md).

Los tipos válidos y los campos que aplican a cada uno salen de
shared/contracts/artifact-types.json, que debe coincidir con artifact-catalog.md.
"""
import json
import re
from pathlib import Path

from .errors import InvalidMetadata
from .ids import is_valid_id, is_valid_ref

USER_PRODUCER = "usuario"

_ISO_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_DRIVE = re.compile(r"[A-Za-z]:")
_TYPED_FIELDS = ("log_name", "scenario", "rule", "variant")
_KNOWN_KEYS = frozenset(
    [
        "schema_version", "artifact_id", "run_id", "task_id", "producer", "type",
        "status", "status_reason", "created_at", "log_name", "scenario", "rule",
        "variant", "depends_on", "files", "attributes",
    ]
)
_RULE_KEYS = frozenset(["kind", "path", "variation"])
_FILE_KEYS = frozenset(["path", "size_bytes", "sha256"])


def default_registry_path():
    return Path(__file__).resolve().parents[1] / "contracts" / "artifact-types.json"


def load_registry(path=None):
    target = Path(path) if path else default_registry_path()
    with open(str(target), encoding="utf-8") as handle:
        return json.load(handle)


def _text(value):
    return isinstance(value, str) and value.strip() != ""


def _relative_path_ok(path):
    if not _text(path) or path.startswith("/") or "\\" in path or _DRIVE.match(path):
        return False
    return all(part not in ("", ".", "..") for part in path.split("/"))


def validate_metadata(meta, registry, exists=None, check_files=True):
    """Devuelve la lista de reglas incumplidas (vacía si el metadato es válido).

    exists: función opcional exists(ref) -> bool para comprobar `depends_on`.
    check_files: si es False no se exige inventario (validación previa a copiar).
    """
    if not isinstance(meta, dict):
        return ["el metadato debe ser un objeto"]
    problems = []

    for key in meta:
        if key not in _KNOWN_KEYS:
            problems.append("campo desconocido: %s" % key)

    if meta.get("schema_version") != registry["schema_version"]:
        problems.append("schema_version debe ser %r" % registry["schema_version"])
    if not is_valid_id("art", meta.get("artifact_id")):
        problems.append("artifact_id inválido")
    if not is_valid_id("run", meta.get("run_id")):
        problems.append("run_id inválido")
    if not _text(meta.get("producer")):
        problems.append("producer es obligatorio")
    if not (isinstance(meta.get("created_at"), str) and _ISO_UTC.fullmatch(meta["created_at"])):
        problems.append("created_at debe estar en UTC (AAAA-MM-DDTHH:MM:SSZ)")

    if "task_id" in meta:
        if not is_valid_id("task", meta["task_id"]):
            problems.append("task_id inválido")
    elif meta.get("producer") != USER_PRODUCER:
        problems.append("task_id es obligatorio salvo si producer es %r" % USER_PRODUCER)

    status = meta.get("status")
    if status not in registry["statuses"]:
        problems.append("status debe ser uno de %s" % ", ".join(registry["statuses"]))
    if status in ("parcial", "fallido"):
        if not _text(meta.get("status_reason")):
            problems.append("status_reason es obligatorio si el estado es %s" % status)
    elif status == "completo" and "status_reason" in meta:
        problems.append("status_reason no aplica a un artefacto completo")

    type_name = meta.get("type")
    type_spec = registry["types"].get(type_name) if isinstance(type_name, str) else None
    if type_spec is None:
        problems.append("tipo desconocido: %r" % (type_name,))
    else:
        for field in _TYPED_FIELDS:
            mode = type_spec[field]
            if mode == "required" and field not in meta:
                problems.append("falta %s (obligatorio para %s)" % (field, type_name))
            if mode == "forbidden" and field in meta:
                problems.append("%s no aplica a %s" % (field, type_name))

    if "log_name" in meta and not _text(meta["log_name"]):
        problems.append("log_name debe ser un texto no vacío")
    if "scenario" in meta and meta["scenario"] not in registry["scenarios"]:
        problems.append("scenario debe ser uno de %s" % ", ".join(registry["scenarios"]))
    if "variant" in meta and not _text(meta["variant"]):
        problems.append("variant debe ser un texto no vacío")
    if "rule" in meta:
        rule = meta["rule"]
        if not (isinstance(rule, dict) and set(rule.keys()) == _RULE_KEYS
                and all(_text(rule[key]) for key in _RULE_KEYS)):
            problems.append("rule debe tener exactamente kind, path y variation (textos no vacíos)")
    if "attributes" in meta and not isinstance(meta["attributes"], dict):
        problems.append("attributes debe ser un objeto")

    depends = meta.get("depends_on")
    if not isinstance(depends, list):
        problems.append("depends_on debe ser una lista")
    else:
        for ref in depends:
            if not is_valid_ref(ref):
                problems.append("depends_on contiene una referencia inválida")
            elif exists is not None and not exists(ref):
                problems.append("depends_on: no existe %s" % ref["artifact_id"])

    files = meta.get("files")
    if not isinstance(files, list):
        problems.append("files debe ser una lista")
    else:
        seen = set()
        for entry in files:
            if not (isinstance(entry, dict) and set(entry.keys()) == _FILE_KEYS):
                problems.append("files: cada entrada debe tener path, size_bytes y sha256")
                continue
            if not _relative_path_ok(entry["path"]):
                problems.append("files: ruta no permitida (debe ser relativa, con '/', sin '..')")
            if entry["path"] in seen:
                problems.append("files: ruta repetida %s" % entry["path"])
            seen.add(entry["path"])
            size = entry["size_bytes"]
            if not (isinstance(size, int) and not isinstance(size, bool) and size >= 0):
                problems.append("files: size_bytes inválido en %s" % entry["path"])
            if not (isinstance(entry["sha256"], str) and _SHA256.fullmatch(entry["sha256"])):
                problems.append("files: sha256 inválido en %s" % entry["path"])
        if check_files and status == "completo" and not files:
            problems.append("un artefacto completo debe tener al menos un archivo")

    return problems


def ensure_valid(meta, registry, exists=None, check_files=True):
    problems = validate_metadata(meta, registry, exists=exists, check_files=check_files)
    if problems:
        raise InvalidMetadata(problems)
