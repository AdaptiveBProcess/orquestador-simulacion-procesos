"""Errores de la capa de acceso a datos.

Cada error tiene un tipo propio y un `code` estable, para que el runtime
pueda convertirlo en un error de tarea sin interpretar mensajes.
"""


class DataAccessError(Exception):
    """Base de todos los errores de data_access."""

    code = "data_access_error"


class ArtifactNotFound(DataAccessError):
    """La referencia no existe o el artefacto está incompleto (huérfano)."""

    code = "artifact_not_found"


class InvalidMetadata(DataAccessError):
    """El metadato (o una referencia) incumple artifact-metadata.md."""

    code = "invalid_metadata"

    def __init__(self, violations):
        self.violations = list(violations)
        super().__init__("Metadato inválido: " + "; ".join(self.violations))


class IntegrityError(DataAccessError):
    """Los bytes no coinciden con el inventario registrado."""

    code = "integrity_error"

    def __init__(self, message, paths=None):
        self.paths = list(paths or [])
        super().__init__(message)


class ConflictError(DataAccessError):
    """El identificador ya existe."""

    code = "conflict"


class BackendUnavailable(DataAccessError):
    """Disco lleno, sin permisos, ruta inaccesible, etc."""

    code = "backend_unavailable"
