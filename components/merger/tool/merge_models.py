"""Fusión del modelo AS-IS (recursos y llegadas) con el modelo TO-BE (flujo de control).

Origen: legacy/DeclarativeProcessSimulation/support_modules/predictor_adapter.py
(commit 1090059e09cfd4ff1f5d1c8e4d4e84cde45b821b): `extract_tasks`,
`join_tasks_by_name` y `remap_ids_and_transfer_fields` están copiadas sin cambio
de comportamiento. No se importan del repo original porque ese módulo arrastra
TensorFlow (GenerativeLSTM). `merge` reemplaza a `adapt_json` y además devuelve
qué tareas no se pudieron emparejar; el archivo que escribe es idéntico.

Qué hace: parte del JSON TO-BE y le transfiere del AS-IS las llegadas
(`arrival_time_calendar`, `arrival_time_distribution`), los calendarios
(`resource_calendars`) y los recursos (`resource_profiles`,
`task_resource_distribution`), cambiando los identificadores de tarea del AS-IS
por los del TO-BE, emparejando las tareas por nombre sin distinguir mayúsculas.
Las tareas del AS-IS sin pareja en el TO-BE se descartan.
"""
import json
import xml.etree.ElementTree as ET

# ----- Resource Adapter (adapta los recursos del AS-IS al JSON generado)


def extract_tasks(xml_tree):
    """
    Extracts task elements from BPMN XML.
    Returns a dict: {task_name: task_id}
    """
    ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
    root = xml_tree.getroot()

    task_tags = [
        'task', 'userTask', 'serviceTask', 'scriptTask', 'manualTask',
        'businessRuleTask', 'receiveTask', 'sendTask', 'callActivity',
        'startEvent', 'endEvent'
    ]

    tasks = {}
    for tag in task_tags:
        for elem in root.findall(f'.//bpmn:{tag}', ns):
            name = elem.attrib.get('name')
            id_ = elem.attrib.get('id')
            if name:
                tasks[name] = id_
    return tasks


def join_tasks_by_name(file1_path, file2_path):
    """
    Joins two BPMN files by task name (case-insensitive).
    Returns dict: {original_case_task_name: (id_in_file1, id_in_file2)}
    """
    tree1 = ET.parse(file1_path)
    tree2 = ET.parse(file2_path)

    tasks1 = extract_tasks(tree1)
    tasks2 = extract_tasks(tree2)

    # Normalize task names to lowercase for matching
    tasks1_ci = {name.lower(): (name, tid) for name, tid in tasks1.items()}
    tasks2_ci = {name.lower(): (name, tid) for name, tid in tasks2.items()}

    all_normalized_names = set(tasks1_ci.keys()) | set(tasks2_ci.keys())
    result = {}

    for norm_name in all_normalized_names:
        orig_name1, id1 = tasks1_ci.get(norm_name, (None, None))
        orig_name2, id2 = tasks2_ci.get(norm_name, (None, None))

        # Prefer the original name from file1, or fallback to file2
        final_name = orig_name1 or orig_name2
        result[final_name] = (id1, id2)

    return result


def remap_ids_and_transfer_fields(original_json, generated_json, id_mapping):
    # Normalize id_mapping keys to lowercase for case-insensitive access
    normalized_mapping = {name.lower(): (ids[0], ids[1]) for name, ids in id_mapping.items()}
    # Simple replacements
    for key in ["arrival_time_calendar", "arrival_time_distribution", "resource_calendars"]:
        generated_json[key] = original_json.get(key, [])

    # Remap assignedTasks in resource_profiles
    new_profiles = []
    for profile in original_json.get("resource_profiles", []):
        new_resource_list = []
        for res in profile.get("resource_list", []):
            new_tasks = []
            for old_id in res.get("assignedTasks", []):
                # Find name from original task_id
                name = next(
                    (task_name for task_name, (orig_id, _) in normalized_mapping.items()
                     if orig_id == old_id),
                    None
                )
                if name and normalized_mapping[name][1]:
                    new_tasks.append(normalized_mapping[name][1])
            res["assignedTasks"] = new_tasks
            new_resource_list.append(res)
        profile["resource_list"] = new_resource_list
        new_profiles.append(profile)
    generated_json["resource_profiles"] = new_profiles

    # Remap task_id in task_resource_distribution
    new_task_resource_distribution = []
    for item in original_json.get("task_resource_distribution", []):
        old_task_id = item["task_id"]
        name = next(
            (task_name for task_name, (orig_id, _) in normalized_mapping.items()
             if orig_id == old_task_id),
            None
        )
        if name and normalized_mapping[name][1]:
            item["task_id"] = normalized_mapping[name][1]
            new_task_resource_distribution.append(item)
    generated_json["task_resource_distribution"] = new_task_resource_distribution

    return generated_json


# ----- Fusión (reemplaza a `adapt_json` del repo original)


def summarize_mapping(mapping):
    """Qué tareas se emparejaron y cuáles no (por nombre, en orden alfabético)."""
    matched = sorted(n for n, (a, b) in mapping.items() if a and b)
    only_asis = sorted(n for n, (a, b) in mapping.items() if a and not b)
    only_tobe = sorted(n for n, (a, b) in mapping.items() if b and not a)
    return {"matched": matched, "only_asis": only_asis, "only_tobe": only_tobe}


def merge(asis_bpmn_path, asis_json_path, tobe_bpmn_path, tobe_json_path, merged_json_path):
    """Escribe el JSON fusionado y devuelve el resumen del emparejamiento de tareas."""
    with open(asis_json_path, encoding="utf-8") as f:
        original_json = json.load(f)
    with open(tobe_json_path, encoding="utf-8") as f:
        generated_json = json.load(f)

    bpmn_mapping = join_tasks_by_name(asis_bpmn_path, tobe_bpmn_path)
    updated_json = remap_ids_and_transfer_fields(original_json, generated_json, bpmn_mapping)

    with open(merged_json_path, "w", encoding="utf-8") as f:
        json.dump(updated_json, f, indent=4)
    return summarize_mapping(bpmn_mapping)
