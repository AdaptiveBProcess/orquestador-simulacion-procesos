"""Capa de acceso a datos: única vía para leer y escribir artefactos por referencia."""
from .errors import (
    ArtifactNotFound, BackendUnavailable, ConflictError, DataAccessError,
    IntegrityError, InvalidMetadata,
)
from .ids import is_valid_id, is_valid_ref, new_id
from .interface import ArtifactStore
from .local_disk import LocalDiskStore

__all__ = [
    "ArtifactStore", "LocalDiskStore", "new_id", "is_valid_id", "is_valid_ref",
    "DataAccessError", "ArtifactNotFound", "InvalidMetadata", "IntegrityError",
    "ConflictError", "BackendUnavailable",
]
