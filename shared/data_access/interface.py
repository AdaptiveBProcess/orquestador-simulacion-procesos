"""Interfaz de la capa de acceso a datos, independiente del respaldo."""
from abc import ABC, abstractmethod


class ArtifactStore(ABC):
    """Única vía para leer y escribir artefactos, siempre por referencia.

    Una referencia es {"run_id": ..., "artifact_id": ...}. Nunca una ruta.
    """

    @abstractmethod
    def guardar(self, *, run_id, producer, type, status, source_dir=None,
                task_id=None, status_reason=None, log_name=None, scenario=None,
                rule=None, variant=None, depends_on=None, attributes=None):
        """Guarda el contenido de `source_dir` como artefacto y devuelve su referencia.

        Genera artifact_id y created_at, calcula el inventario de archivos y
        valida el metadato. `source_dir` puede omitirse en artefactos parciales
        o fallidos sin contenido.
        """

    @abstractmethod
    def obtener(self, ref, task_id, *, run_id=None, verificar=True):
        """Copia los bytes a la carpeta de trabajo de la tarea.

        `run_id` es la corrida de la tarea (por defecto, la del artefacto).
        Devuelve {"path": carpeta de trabajo, "metadata": metadatos}.
        """

    @abstractmethod
    def leer_metadatos(self, ref):
        """Devuelve los metadatos sin tocar los bytes."""

    @abstractmethod
    def listar(self, run_id, *, type=None, status=None, scenario=None, producer=None):
        """Metadatos de los artefactos de una corrida, con filtros opcionales."""

    @abstractmethod
    def cambiar_estado(self, ref, status, status_reason=None):
        """Cambia solo status y status_reason; devuelve los metadatos nuevos."""
