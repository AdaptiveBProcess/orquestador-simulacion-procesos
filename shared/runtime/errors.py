"""Errores del runtime que se lanzan al llamador (no se guardan en la tarea).

Una solicitud mal formada, sin identificadores válidos, no se puede registrar
como tarea; por eso se rechaza con una excepción. El resto de fallos quedan
como resultado `fallida` dentro del registro de la tarea.
"""


class RuntimeServiceError(Exception):
    code = "runtime_error"


class InvalidRequest(RuntimeServiceError):
    """La solicitud no tiene la forma del contrato."""

    code = "invalid_request"


class TaskConflict(RuntimeServiceError):
    """El task_id ya existe con otra solicitud o en otra corrida."""

    code = "task_conflict"


class TaskNotFound(RuntimeServiceError):
    code = "task_not_found"
