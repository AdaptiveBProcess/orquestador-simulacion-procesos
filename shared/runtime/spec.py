"""Cómo un componente se describe ante el cascarón de servicio.

Un adaptador declara, por cada tarea: entradas, parámetros,
salidas y la función que hace el trabajo. El runtime se encarga de todo lo
demás (validar, materializar entradas, verificar salidas, registrar, responder).
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class TaskFailure(Exception):
    """Fallo controlado de una tarea. Puede traer salidas parciales para registrar."""

    def __init__(self, code, message, retryable=False, outputs=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.outputs = outputs or {}


@dataclass
class InputSpec:
    type: str                      # tipo de artefacto del catálogo
    required: bool = True
    allow_partial: bool = False    # acepta artefactos en estado parcial


@dataclass
class ParamSpec:
    kind: Any = None               # tipo Python o tupla de tipos; None = sin comprobar
    default: Any = None
    required: bool = False
    choices: Optional[List[Any]] = None
    description: str = ""


@dataclass
class OutputSpec:
    type: str                      # tipo de artefacto del catálogo
    required: bool = True
    # Patrones (glob, relativos a la carpeta de salida) que deben tener al menos
    # un archivo. Es lo que impide dar por buena una salida que no se produjo.
    required_files: List[str] = field(default_factory=list)


@dataclass
class TaskSpec:
    name: str
    execute: Callable              # execute(ctx) -> {nombre_de_salida: {...}}
    inputs: Dict[str, InputSpec] = field(default_factory=dict)
    params: Dict[str, ParamSpec] = field(default_factory=dict)
    outputs: Dict[str, OutputSpec] = field(default_factory=dict)
    preconditions: Optional[Callable] = None   # preconditions(ctx) -> [mensajes]
    description: str = ""


@dataclass
class ComponentSpec:
    name: str
    tasks: Dict[str, TaskSpec]
    max_concurrent: int = 1
    contract_version: str = "v0"


class TaskContext(object):
    """Lo que recibe la función de una tarea.

    inputs: {nombre: {"ref": ref, "path": carpeta materializada, "metadata": metadatos}}
    params: parámetros efectivos (con defectos aplicados)
    """

    def __init__(self, run_id, task_id, task, inputs, params, work_dir, report):
        self.run_id = run_id
        self.task_id = task_id
        self.task = task
        self.inputs = inputs
        self.params = params
        self.work_dir = work_dir
        self._report = report

    def output_dir(self, name):
        """Carpeta donde la tarea deja la salida `name` (se crea si no existe)."""
        path = Path(self.work_dir) / "out" / name
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def report(self, message):
        """Deja un mensaje de avance que se puede consultar mientras corre."""
        self._report(str(message))
