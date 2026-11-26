"""Componente de ejemplo: consumidor de notas (ver README.md de esta carpeta).

Tarea `consumer.informar`: recibe una nota por referencia y produce un informe
(`example.report`). `min_caracteres` permite incumplir una precondición de
contenido; `mode` provoca fallos.
"""
import logging
import time
from pathlib import Path

from shared.data_access import LocalDiskStore
from shared.runtime import ComponentSpec, InputSpec, OutputSpec, ParamSpec, Runtime, TaskSpec, serve

MODES = ["normal", "fallo", "sin_salida"]


def _leer_nota(ctx):
    return (Path(ctx.inputs["nota"]["path"]) / "note.txt").read_text(encoding="utf-8")


def precondiciones(ctx):
    try:
        text = _leer_nota(ctx).strip()
    except OSError:
        return ["la nota no contiene note.txt"]
    minimo = ctx.params["min_caracteres"]
    if len(text) < minimo:
        return ["la nota tiene %d caracteres útiles y se exigen al menos %d" % (len(text), minimo)]
    return []


def informar(ctx):
    mode = ctx.params["mode"]
    ctx.report("iniciando (modo %s)" % mode)
    time.sleep(ctx.params["sleep"])
    if mode == "fallo":
        raise RuntimeError("fallo forzado por el parámetro mode")
    if mode == "sin_salida":
        return {"informe": {}}  # sin escribir report.txt
    text = _leer_nota(ctx)
    report = Path(ctx.output_dir("informe")) / "report.txt"
    report.write_text(
        "Informe\ncaracteres: %d\npalabras: %d\ntexto: %s\n" % (len(text), len(text.split()), text),
        encoding="utf-8",
    )
    return {"informe": {}}


component = ComponentSpec(
    name="consumer",
    max_concurrent=1,
    tasks={
        "informar": TaskSpec(
            name="informar",
            execute=informar,
            preconditions=precondiciones,
            description="Produce un informe a partir de una nota.",
            inputs={"nota": InputSpec("example.note")},
            params={
                "min_caracteres": ParamSpec(int, 1, description="Mínimo de caracteres útiles que debe tener la nota"),
                "mode": ParamSpec(str, "normal", choices=MODES, description="Comportamiento a provocar"),
                "sleep": ParamSpec((int, float), 0, description="Segundos de espera antes de trabajar"),
            },
            outputs={"informe": OutputSpec("example.report", required_files=["report.txt"])},
        )
    },
)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    serve(Runtime(component, LocalDiskStore()))


if __name__ == "__main__":
    main()
