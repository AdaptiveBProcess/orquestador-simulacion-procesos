"""Componente Simod: descubre un modelo de simulación de procesos desde un log de eventos.

Dos tareas con la misma lógica y distinta entrada:
  simod.descubrir_asis  -> log: declarative.event_log      (escenario AS-IS)
  simod.descubrir_tobe  -> log: declarative.generated_log  (escenario TO-BE)
Las dos reciben `config` (declarative.simod_config) y producen `modelo`
(declarative.simulation_model): el contenido de `best_result` de Simod.
"""
import os
import shlex
import shutil
from pathlib import Path

from shared.runtime import ComponentSpec, InputSpec, OutputSpec, ParamSpec, TaskFailure, TaskSpec

from components.simod.tool import event_log as elog
from components.simod.tool import simod_config as scfg
from components.simod.tool import simod_runner as runner

DEFAULT_HOME = "/usr/src/Simod"
DEFAULT_COMMAND = "poetry run simod"


def _home():
    return os.environ.get("ORQ_SIMOD_HOME") or DEFAULT_HOME


def _command():
    return os.environ.get("ORQ_SIMOD_COMMAND") or DEFAULT_COMMAND


def _resolve(ctx):
    """Localiza el log y la configuración de las entradas. Devuelve (log, config_text, config, problemas)."""
    problems = []
    log_file = config_text = config = None
    try:
        log_file = elog.find_log_file(ctx.inputs["log"]["path"])
    except elog.LogError as exc:
        problems.append(str(exc))
    yamls = sorted(p for pattern in ("*.yaml", "*.yml") for p in Path(ctx.inputs["config"]["path"]).rglob(pattern))
    if len(yamls) != 1:
        problems.append("la configuración debe traer exactamente un archivo .yaml (hay %d)" % len(yamls))
    else:
        try:
            config_text = yamls[0].read_text(encoding="utf-8")
            config = scfg.load(config_text)
        except (OSError, UnicodeDecodeError):
            problems.append("no se pudo leer la configuración")
        except scfg.ConfigError as exc:
            problems.append(str(exc))
    return log_file, config_text, config, problems


def _preconditions(ctx):
    problems = []
    if not runner.command_available(_command()):
        problems.append("no se encontró el comando de Simod")
    if not Path(_home()).is_dir():
        problems.append("no existe el directorio de trabajo de Simod")
    log_file, _text, config, found = _resolve(ctx)
    problems.extend(found)
    if not found:
        try:
            cases = elog.count_cases(log_file, scfg.case_column(config))
        except (elog.LogError, OSError, UnicodeDecodeError) as exc:
            problems.append("no se pudo contar los casos del log: %s" % exc)
        else:
            if cases < ctx.params["min_casos"]:
                problems.append("el log tiene %d casos y se exigen al menos %d "
                                "(con menos, la validación 80/20 queda sin casos)" % (cases, ctx.params["min_casos"]))
    return problems


def _partial(ctx, target, log_path, scenario, log_name):
    """Salida parcial con la evidencia de una ejecución que no produjo un modelo completo."""
    if not ctx.params["conservar_parcial"] or target is None or not Path(target).is_dir():
        return {}
    try:
        shutil.copyfile(str(log_path), str(Path(target) / "simod.log"))
    except OSError:
        pass
    result = {"source_dir": str(target), "scenario": scenario}
    if log_name:
        result["log_name"] = log_name
    return {"modelo": result}


def _discover(ctx, scenario):
    log_file, config_text, config, problems = _resolve(ctx)
    if problems:
        raise TaskFailure("invalid_input", "; ".join(problems))
    log_name = ctx.inputs["log"]["metadata"].get("log_name")
    work = Path(ctx.work_dir)

    stage = work / "simod_in"
    gz = elog.prepare_gz(log_file, stage)
    config_path = stage / "configuration.yaml"
    config_path.write_text(scfg.with_train_log(config_text, gz.name), encoding="utf-8")
    output_dir = work / "simod_out"
    log_path = work / "simod.log"

    ctx.report("ejecutando Simod (%s)" % scenario)
    result = runner.run_simod(
        _command(), _home(), config_path, output_dir, log_path, ctx.params["timeout_segundos"],
        on_tick=lambda seconds: ctx.report("Simod sigue en ejecución (%d s)" % seconds),
    )
    best, run_dir = runner.locate_results(output_dir)
    evidence = run_dir or output_dir

    if result.timed_out:
        raise TaskFailure("timeout", "Simod superó el límite de %s s y fue detenido" % ctx.params["timeout_segundos"],
                          outputs=_partial(ctx, evidence, log_path, scenario, log_name))
    if result.returncode != 0:
        raise TaskFailure("simod_failed", "Simod terminó con código %s: %s" % (
                              result.returncode, runner.log_tail(log_path)),
                          outputs=_partial(ctx, evidence, log_path, scenario, log_name))

    files = runner.model_files(best)
    if files is None:
        # Terminó sin error pero sin un modelo completo: se registra lo que haya como parcial.
        ctx.report("Simod terminó sin un modelo completo en best_result")
        return _partial(ctx, evidence, log_path, scenario, log_name)
    ctx.report("modelo descubierto: %s" % files[0])
    out = {"source_dir": str(best), "scenario": scenario,
           "attributes": {"model_name": Path(files[0]).stem, "bpmn_file": files[0], "json_file": files[1]}}
    if log_name:
        out["log_name"] = log_name
    return {"modelo": out}


def _task(name, scenario, log_type, description):
    return TaskSpec(
        name=name,
        description=description,
        execute=lambda ctx: _discover(ctx, scenario),
        preconditions=_preconditions,
        inputs={"log": InputSpec(log_type), "config": InputSpec("declarative.simod_config")},
        params={
            "min_casos": ParamSpec(int, 5, description="Mínimo de casos del log (menos deja la validación 80/20 vacía)"),
            "timeout_segundos": ParamSpec((int, float), 3600, description="Tiempo máximo de ejecución de Simod"),
            "conservar_parcial": ParamSpec(bool, True, description="Registrar como parcial lo producido si Simod falla"),
        },
        outputs={"modelo": OutputSpec("declarative.simulation_model", required_files=["*.bpmn", "*.json"])},
    )


component = ComponentSpec(
    name="simod",
    max_concurrent=1,
    tasks={
        "descubrir_asis": _task("descubrir_asis", "AS-IS", "declarative.event_log",
                                "Descubre el modelo de simulación AS-IS a partir del log original."),
        "descubrir_tobe": _task("descubrir_tobe", "TO-BE", "declarative.generated_log",
                                "Descubre el modelo de simulación TO-BE a partir del log generado."),
    },
)
