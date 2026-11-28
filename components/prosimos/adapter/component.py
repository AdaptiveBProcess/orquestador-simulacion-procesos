"""Componente Prosimos: simula el modelo TO-BE fusionado y produce un log y estadísticas.

Tarea `prosimos.simular`:
  entradas: modelo (declarative.simulation_model, escenario TO-BE), fusionado (declarative.merged_model)
  salida:   resultado (declarative.simulation_result): <modelo>_prosimos_log.csv,
            <modelo>_prosimos_stats.csv y, si Prosimos lo genera, simulation_warnings.txt
"""
import json
import os
import shutil
from pathlib import Path

from shared.runtime import ComponentSpec, InputSpec, OutputSpec, ParamSpec, TaskFailure, TaskSpec
from shared.runtime.process import command_available, log_tail, run_process

from components.prosimos.tool import prosimos_runner as tool

DEFAULT_HOME = "/usr/src/Simod"
DEFAULT_COMMAND = "poetry run prosimos"


def _home():
    return os.environ.get("ORQ_PROSIMOS_HOME") or DEFAULT_HOME


def _command():
    return os.environ.get("ORQ_PROSIMOS_COMMAND") or DEFAULT_COMMAND


def _resolve(ctx):
    """Localiza el BPMN y el JSON fusionado. Devuelve (bpmn, json, problemas)."""
    problems = []
    model = ctx.inputs["modelo"]
    meta = model["metadata"]
    if meta.get("scenario") != "TO-BE":
        problems.append("Prosimos simula el modelo TO-BE y recibió el escenario %s" % meta.get("scenario"))

    base = Path(model["path"])
    bpmn = None
    wanted = (meta.get("attributes") or {}).get("bpmn_file")
    if wanted and (base / wanted).is_file():
        bpmn = base / wanted
    else:
        found = sorted(base.glob("*.bpmn"))
        if len(found) == 1:
            bpmn = found[0]
        else:
            problems.append("el modelo debe traer exactamente un archivo .bpmn (hay %d)" % len(found))

    merged = None
    found = sorted(Path(ctx.inputs["fusionado"]["path"]).glob("*.json"))
    if len(found) != 1:
        problems.append("el modelo fusionado debe traer exactamente un archivo .json (hay %d)" % len(found))
    else:
        try:
            if not isinstance(json.loads(found[0].read_text(encoding="utf-8")), dict):
                problems.append("el modelo fusionado no es un objeto JSON")
            else:
                merged = found[0]
        except (OSError, ValueError):
            problems.append("el modelo fusionado no es un JSON válido")
    return bpmn, merged, problems


def _preconditions(ctx):
    problems = []
    if not command_available(_command()):
        problems.append("no se encontró el comando de Prosimos")
    if not Path(_home()).is_dir():
        problems.append("no existe el directorio de trabajo de Prosimos")
    if ctx.params["total_cases"] < 1:
        problems.append("total_cases debe ser al menos 1")
    problems.extend(_resolve(ctx)[2])
    return problems


def _partial(ctx, out, log_path):
    """Evidencia de una ejecución que no produjo un resultado utilizable."""
    if not ctx.params["conservar_parcial"]:
        return {}
    try:
        shutil.copyfile(str(log_path), str(Path(out) / "prosimos.log"))
    except OSError:
        pass
    evidence = {"rule": ctx.inputs["fusionado"]["metadata"]["rule"]}
    if ctx.inputs["modelo"]["metadata"].get("log_name"):
        evidence["log_name"] = ctx.inputs["modelo"]["metadata"]["log_name"]
    return {"resultado": evidence}


def _simulate(ctx):
    bpmn, merged, problems = _resolve(ctx)
    if problems:
        raise TaskFailure("invalid_input", "; ".join(problems))
    meta_model = ctx.inputs["modelo"]["metadata"]
    meta_merged = ctx.inputs["fusionado"]["metadata"]

    out = Path(ctx.output_dir("resultado"))
    stem = bpmn.stem
    log_csv = out / (stem + "_prosimos_log.csv")
    stats_csv = out / (stem + "_prosimos_stats.csv")
    prosimos_log = Path(ctx.work_dir) / "prosimos.log"

    tool.clear_stale_warnings(_home())
    argv = tool.build_argv(_command(), bpmn, merged, ctx.params["total_cases"], log_csv, stats_csv)
    ctx.report("ejecutando Prosimos (%d casos)" % ctx.params["total_cases"])
    result = run_process(argv, _home(), prosimos_log, ctx.params["timeout_segundos"],
                         on_tick=lambda s: ctx.report("Prosimos sigue en ejecución (%d s)" % s))
    has_warnings = tool.collect_warnings(_home(), out)

    if result.timed_out:
        raise TaskFailure("timeout", "Prosimos superó el límite de %s s y fue detenido" % ctx.params["timeout_segundos"],
                          outputs=_partial(ctx, out, prosimos_log))
    if result.returncode != 0:
        raise TaskFailure("prosimos_failed", "Prosimos terminó con código %s: %s" % (
                              result.returncode, log_tail(prosimos_log)),
                          outputs=_partial(ctx, out, prosimos_log))
    empty = [p.name for p in (log_csv, stats_csv) if p.exists() and not tool.has_content(p)]
    if empty:
        raise TaskFailure("empty_output", "Prosimos terminó sin error pero dejó vacío: %s" % ", ".join(empty),
                          outputs=_partial(ctx, out, prosimos_log))
    if has_warnings:
        ctx.report("Prosimos generó avisos de simulación (simulation_warnings.txt)")

    result_meta = {
        "rule": meta_merged["rule"],
        "attributes": {"tool": "prosimos", "model_name": stem, "total_cases": int(ctx.params["total_cases"])},
    }
    if meta_model.get("log_name"):
        result_meta["log_name"] = meta_model["log_name"]
    return {"resultado": result_meta}


component = ComponentSpec(
    name="prosimos",
    max_concurrent=1,
    tasks={
        "simular": TaskSpec(
            name="simular",
            description="Simula el modelo TO-BE fusionado con Prosimos.",
            execute=_simulate,
            preconditions=_preconditions,
            inputs={
                "modelo": InputSpec("declarative.simulation_model"),
                "fusionado": InputSpec("declarative.merged_model"),
            },
            params={
                "total_cases": ParamSpec(int, 20, description="Número de casos a simular"),
                "timeout_segundos": ParamSpec((int, float), 1800, description="Tiempo máximo de Prosimos"),
                "conservar_parcial": ParamSpec(bool, True, description="Registrar como parcial lo producido si Prosimos falla"),
            },
            outputs={
                "resultado": OutputSpec("declarative.simulation_result",
                                        required_files=["*_prosimos_log.csv", "*_prosimos_stats.csv"]),
            },
        )
    },
)
