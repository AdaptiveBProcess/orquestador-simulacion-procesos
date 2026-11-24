# Catálogo de artefactos

Todo lo que un componente consume o produce es un **artefacto** registrado, y se referencia por su identificador, nunca por una ruta. Este catálogo sale de los archivos reales de la línea base (`docs/baseline/BASELINE.md`).

## Vocabulario

- **Proyecto/log:** el proceso de negocio sobre el que se trabaja.
- **Corrida (`run_id`):** una ejecución completa e identificable. Reemplaza a "la última carpeta".
- **Tarea (`task_id`):** una unidad de trabajo de un componente dentro de una corrida. Una corrida tiene varias tareas.
- **Artefacto:** un archivo (o conjunto de archivos) con tipo, corrida, productor y estado.
- **Registro:** el índice que dice qué artefactos existen y dónde están sus bytes.

## Metadatos obligatorios

| Campo | Contenido |
|---|---|
| `artifact_id` | Identificador único |
| `type` | Tipo del catálogo, con prefijo de dominio (`declarative.*`) |
| `run_id` / `task_id` | Corrida y tarea que lo produjo |
| `depends_on` | Artefactos de los que se derivó (por ejemplo, el AS-IS usado en una fusión) |
| `log_name` | Proyecto/log al que pertenece |
| `scenario` | `AS-IS` o `TO-BE`, cuando aplica |
| `rule` / `variant` | Regla (ruta y variación) y variante de generación, cuando aplican |
| `created_at` | UTC |
| `status` | `completo`, `parcial` o `fallido` |

Los artefactos de tareas fallidas se registran con su estado; no se descartan.

## Catálogo inicial

| Tipo | Archivos reales | Productor | Consumidores |
|---|---|---|---|
| `declarative.event_log` | `<log>.csv` y `.csv.gz` | Usuario | Trainer, Simod |
| `declarative.rules` | `rules.ini` (regla y variación) | Usuario / Declarative | Predictor |
| `declarative.embeddings` | `ac_*.emb`, `rl_*.emb` | Trainer | Trainer (caché) |
| `declarative.model_package` | `.h5`, `model_parameters.json`, `<log>_ASIS.csv`, `test_log.csv` | Trainer | Predictor |
| `declarative.optimization_results` | `OP_*.csv` | Trainer | Informativo |
| `declarative.generated_log` | `.csv`, `.csv.gz`, `.xes` | Predictor | Simod (TO-BE) |
| `declarative.prediction_diagnostics` | `SE_*.csv`, `tst_*.csv`, `gen_*_1.csv` | Predictor | Informativo |
| `declarative.simod_config` | `configuration_original.yaml`, `configuration_generated.yaml` | Usuario | Simod |
| `declarative.simulation_model` | `.bpmn`, `.json`, `canonical_model.json`, `configuration.yaml`, `runtimes.json`, `*_iterations_measures.csv` (en `best_result`) | Simod | Merger, Prosimos, BIMP |
| `declarative.merged_model` | `*_merged.json` | Merger | Prosimos, BIMP |
| `declarative.bimp_model` | `*_bimp_version.bpmn` | BIMP | BIMP |
| `declarative.simulation_result` | `*_prosimos_log.csv`, `*_prosimos_stats.csv`, `simulation_warnings.txt`; `*_bimp_log.csv` | Prosimos, BIMP | Analytics, Chat |

### Ajuste respecto al borrador del paso 3

`*_bimp_version.bpmn` lo produce el paso "embed simulation" (`bimp_parser.embed_qbp_simulation`), que toma el BPMN TO-BE y el modelo fusionado. Es un paso propio de BIMP, así que ese artefacto pertenece al componente BIMP y no al Merger. El Merger produce solo `declarative.merged_model`.

## Tipos y proyectos nuevos

Cada proyecto agrega sus tipos con su prefijo. Cuando dos proyectos compartan un tipo genérico (por ejemplo, el log de eventos), se promueve a un prefijo común (`core.*`) sin cambiar el contrato.

## Artefactos parciales y precondiciones que el catálogo debe cubrir

- **Parciales:** la carpeta TO-BE de la corrida 1 (con `best_result` vacío) se registra con estado `parcial` o `fallido`.
- **Precondición de Simod:** el log recibido debe tener suficientes casos para que la partición 80/20 deje casos de validación. Con 4 casos falló.
