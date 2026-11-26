"""Cascarón de servicio: lo que todo componente hace al recibir una tarea."""
from .engine import EN_COLA, EN_EJECUCION, EXITOSA, FALLIDA, PARCIAL, Runtime
from .errors import InvalidRequest, RuntimeServiceError, TaskConflict, TaskNotFound
from .http_service import make_server, serve
from .spec import (
    ComponentSpec, InputSpec, OutputSpec, ParamSpec, TaskContext, TaskFailure, TaskSpec,
)

__all__ = [
    "Runtime", "ComponentSpec", "TaskSpec", "InputSpec", "ParamSpec", "OutputSpec",
    "TaskContext", "TaskFailure", "InvalidRequest", "TaskConflict", "TaskNotFound",
    "RuntimeServiceError", "EN_COLA", "EN_EJECUCION", "EXITOSA", "FALLIDA", "PARCIAL",
    "make_server", "serve",
]
