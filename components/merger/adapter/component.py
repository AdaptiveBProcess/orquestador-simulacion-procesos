"""Componente Merger: fusiona el modelo AS-IS con el TO-BE para simular.

Tarea `merger.fusionar`:
  entradas: asis  (declarative.simulation_model, escenario AS-IS)
            tobe  (declarative.simulation_model, escenario TO-BE)
            regla (declarative.rules): de aquí sale la metainformación `rule`
  salida:   fusionado (declarative.merged_model): <modelo TO-BE>_merged.json
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from shared.runtime import ComponentSpec, InputSpec, OutputSpec, TaskFailure, TaskSpec

from components.merger.tool import merge_models as tool

REQUIRED_ASIS_KEYS = ("resource_profiles", "task_resource_distribution")


def _locate(entry, label, expected_scenario):
    """BPMN y JSON de recursos de un modelo. Devuelve (bpmn, json, problemas)."""
    problems = []
    meta = entry["metadata"]
    base = Path(entry["path"])
    if meta.get("scenario") != expected_scenario:
        problems.append("el modelo %s debe ser del escenario %s y recibió %s"
                        % (label, expected_scenario, meta.get("scenario")))
    attrs = meta.get("attributes") or {}

    bpmn = None
    wanted = attrs.get("bpmn_file")
    if wanted and (base / wanted).is_file():
        bpmn = base / wanted
    else:
        found = sorted(base.glob("*.bpmn"))
        if len(found) == 1:
            bpmn = found[0]
        else:
            problems.append("el modelo %s debe traer exactamente un archivo .bpmn (hay %d)" % (label, len(found)))

    resources = None
    if bpmn is not None:
        name = attrs.get("json_file") if wanted == bpmn.name else None
        candidate = base / (name or (bpmn.stem + ".json"))
        if candidate.is_file():
            resources = candidate
        else:
            problems.append("al modelo %s le falta el JSON de recursos %s" % (label, candidate.name))
    return bpmn, resources, problems


def _resolve(ctx):
    asis = _locate(ctx.inputs["asis"], "AS-IS", "AS-IS")
    tobe = _locate(ctx.inputs["tobe"], "TO-BE", "TO-BE")
    return asis[:2], tobe[:2], asis[2] + tobe[2]


def _preconditions(ctx):
    (asis_bpmn, asis_json), (tobe_bpmn, tobe_json), problems = _resolve(ctx)
    if not ctx.inputs["tobe"]["metadata"].get("log_name"):
        problems.append("el modelo TO-BE no tiene log_name")
    for label, path in (("AS-IS", asis_bpmn), ("TO-BE", tobe_bpmn)):
        if path is not None:
            try:
                ET.parse(str(path))
            except (ET.ParseError, OSError):
                problems.append("el BPMN %s no es un XML válido" % label)
    for label, path in (("AS-IS", asis_json), ("TO-BE", tobe_json)):
        if path is None:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            problems.append("el JSON %s no es válido" % label)
            continue
        if not isinstance(data, dict):
            problems.append("el JSON %s no es un objeto" % label)
        elif label == "AS-IS":
            for key in REQUIRED_ASIS_KEYS:
                if key not in data:
                    problems.append("al JSON AS-IS le falta `%s`" % key)
    return problems


def _merge(ctx):
    (asis_bpmn, asis_json), (tobe_bpmn, tobe_json), problems = _resolve(ctx)
    if problems:
        raise TaskFailure("invalid_input", "; ".join(problems))
    out = Path(ctx.output_dir("fusionado"))
    merged = out / (tobe_bpmn.stem + "_merged.json")
    ctx.report("fusionando AS-IS y TO-BE")
    try:
        summary = tool.merge(asis_bpmn, asis_json, tobe_bpmn, tobe_json, merged)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise TaskFailure("merge_failed", "no se pudo fusionar los modelos: %s: %s" % (exc.__class__.__name__, exc))
    if summary["only_tobe"] or summary["only_asis"]:
        ctx.report("tareas sin pareja: %d solo en AS-IS, %d solo en TO-BE"
                   % (len(summary["only_asis"]), len(summary["only_tobe"])))
    return {"fusionado": {
        "log_name": ctx.inputs["tobe"]["metadata"]["log_name"],
        "rule": ctx.inputs["regla"]["metadata"]["rule"],
        "attributes": {
            "model_name": tobe_bpmn.stem,
            "merged_file": merged.name,
            "matched_tasks": len(summary["matched"]),
            "only_asis_tasks": summary["only_asis"],
            "only_tobe_tasks": summary["only_tobe"],
        },
    }}


component = ComponentSpec(
    name="merger",
    max_concurrent=2,
    tasks={
        "fusionar": TaskSpec(
            name="fusionar",
            description="Fusiona el modelo AS-IS (recursos y llegadas) con el TO-BE (flujo de control).",
            execute=_merge,
            preconditions=_preconditions,
            inputs={
                "asis": InputSpec("declarative.simulation_model"),
                "tobe": InputSpec("declarative.simulation_model"),
                "regla": InputSpec("declarative.rules"),
            },
            outputs={"fusionado": OutputSpec("declarative.merged_model", required_files=["*_merged.json"])},
        )
    },
)
