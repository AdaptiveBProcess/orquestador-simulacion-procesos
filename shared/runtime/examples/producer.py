"""Componente de ejemplo: productor de notas (ver README.md de esta carpeta).

Tarea `producer.generar`: escribe un texto en `note.txt` y lo entrega como un
artefacto `example.note`. El parámetro `mode` provoca cada comportamiento que
el runtime debe manejar.
"""
import logging
import time
from pathlib import Path

from shared.data_access import LocalDiskStore
from shared.runtime import (
    ComponentSpec, OutputSpec, ParamSpec, Runtime, TaskFailure, TaskSpec, serve,
)

MODES = ["normal", "fallo", "fallo_parcial", "sin_salida", "parcial"]


def generar(ctx):
    mode = ctx.params["mode"]
    ctx.report("iniciando (modo %s)" % mode)
    time.sleep(ctx.params["sleep"])
    note = Path(ctx.output_dir("nota")) / "note.txt"

    if mode == "sin_salida":
        # Termina sin error, pero no produjo lo declarado (el caso de BIMP).
        ctx.report("terminé sin escribir la nota")
        return {"nota": {}}

    note.write_text(ctx.params["text"], encoding="utf-8")
    if mode == "fallo":
        raise RuntimeError("fallo forzado por el parámetro mode")
    if mode == "fallo_parcial":
        raise TaskFailure("fallo_forzado", "fallo forzado con una nota a medias",
                          outputs={"nota": {}})
    if mode == "parcial":
        return {"nota": {"status": "parcial", "status_reason": "nota declarada como parcial"}}
    ctx.report("nota escrita")
    return {"nota": {}}


component = ComponentSpec(
    name="producer",
    max_concurrent=1,
    tasks={
        "generar": TaskSpec(
            name="generar",
            execute=generar,
            description="Genera una nota de texto.",
            params={
                "text": ParamSpec(str, "hola desde el productor", description="Contenido de la nota"),
                "mode": ParamSpec(str, "normal", choices=MODES,
                                  description="Comportamiento a provocar"),
                "sleep": ParamSpec((int, float), 0, description="Segundos de espera antes de trabajar"),
            },
            outputs={"nota": OutputSpec("example.note", required_files=["note.txt"])},
        )
    },
)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    serve(Runtime(component, LocalDiskStore()))


if __name__ == "__main__":
    main()
