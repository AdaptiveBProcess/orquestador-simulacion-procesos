"""Identificadores (ver shared/contracts/identifiers.md).

Formato: <tipo>_<AAAAMMDDTHHMMSSZ>_<8 hex>. Son opacos para los componentes.
"""
import re
import secrets
from datetime import datetime, timezone

KINDS = ("run", "task", "art")
_PATTERNS = dict(
    (kind, re.compile(r"%s_\d{8}T\d{6}Z_[0-9a-f]{8}" % kind)) for kind in KINDS
)


def new_id(kind, now=None):
    """Genera un identificador nuevo del tipo indicado (run, task o art)."""
    if kind not in KINDS:
        raise ValueError(f"tipo de identificador desconocido: {kind}")
    moment = now or datetime.now(timezone.utc)
    return "%s_%s_%s" % (kind, moment.strftime("%Y%m%dT%H%M%SZ"), secrets.token_hex(4))


def is_valid_id(kind, value):
    pattern = _PATTERNS.get(kind)
    return pattern is not None and isinstance(value, str) and pattern.fullmatch(value) is not None


def is_valid_ref(ref):
    """Una referencia es exactamente el par (run_id, artifact_id)."""
    return (
        isinstance(ref, dict)
        and set(ref.keys()) == {"run_id", "artifact_id"}
        and is_valid_id("run", ref["run_id"])
        and is_valid_id("art", ref["artifact_id"])
    )


def utc_now_iso():
    """Fecha y hora UTC para `created_at` (termina en Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
