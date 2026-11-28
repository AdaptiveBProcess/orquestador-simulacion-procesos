# Componente: Merger

**Propósito:** fusionar el modelo AS-IS (llegadas, calendarios y recursos) con el modelo TO-BE (flujo de control) para poder simularlo.
**Tarea:** `merger.fusionar`
**Lógica:** copiada de `legacy/.../predictor_adapter.py` (`join_tasks_by_name`, `remap_ids_and_transfer_fields`, `adapt_json`), sin cambio de comportamiento.

## Entradas
- `asis`: `declarative.simulation_model` del escenario AS-IS.
- `tobe`: `declarative.simulation_model` del escenario TO-BE.
- `regla`: `declarative.rules`; de aquí sale la metainformación `rule` del resultado.
De cada modelo se usa su `.bpmn` y su `<nombre>.json` (los que indica `attributes`, o el único `.bpmn` y su `.json`).

## Parámetros
- Ninguno.

## Salidas
- `fusionado`: `declarative.merged_model` con `<modelo TO-BE>_merged.json`. `attributes` lleva `model_name`, `merged_file`, `matched_tasks`, `only_asis_tasks` y `only_tobe_tasks`.

## Precondiciones
- Los escenarios son los esperados; cada modelo trae un `.bpmn` único y válido y su JSON de recursos.
- El JSON AS-IS contiene `resource_profiles` y `task_resource_distribution`; el TO-BE tiene `log_name`.

## Comportamiento
- Las tareas del AS-IS sin pareja en el TO-BE se descartan (como en el original) y quedan registradas en `attributes`.
- Fallo al fusionar: `fallida` (`merge_failed`) con la causa.

## Despliegue
- **Versión del contrato:** v0.
- **Imagen:** `python:3.11-slim`, sin dependencias.
- **Toma de `legacy/`:** la lógica de fusión, copiada; no se importa nada en tiempo de ejecución.
- **Recursos:** hasta 2 tareas simultáneas. Corre como root, por el volumen compartido.