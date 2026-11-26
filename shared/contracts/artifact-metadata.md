# Metadatos de artefactos (especificación)

Versión: **v0 (borrador)**. Es la fuente para el esquema validable (JSON Schema). Los tipos válidos los define `artifact-catalog.md`; los identificadores, `identifiers.md`.

Un artefacto es **una carpeta** que conserva nombres y subcarpetas (el paquete de modelo, por ejemplo, tiene su `.h5` y una subcarpeta `parameters/`). Junto a esa carpeta, `data_access` guarda un metadato con estos campos.

## Campos comunes

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `schema_version` | texto | Sí | `"0"` |
| `artifact_id` | identificador `art_…` | Sí | Lo genera `data_access` al guardar |
| `run_id` | identificador `run_…` | Sí | Corrida a la que pertenece |
| `task_id` | identificador `task_…` | Sí, salvo si `producer` es `usuario` | Tarea que lo produjo |
| `producer` | texto | Sí | Componente que lo produjo (`trainer`, `predictor`, `simod`…) o `usuario` |
| `type` | texto | Sí | Tipo del catálogo, con prefijo de dominio |
| `status` | `completo`, `parcial` o `fallido` | Sí | Estado del artefacto |
| `status_reason` | texto | Solo si `parcial` o `fallido` | Por qué no está completo |
| `created_at` | fecha y hora UTC (termina en `Z`) | Sí | Fecha oficial; la del identificador es solo orientativa |
| `log_name` | texto | Sí en tipos `declarative.*` | Proyecto/log al que pertenece |
| `depends_on` | lista de referencias `(run_id, artifact_id)` | No (vacía por defecto) | Artefactos de los que se derivó |
| `files` | lista de `{path, size_bytes, sha256}` | Sí (puede ir vacía si es `parcial` o `fallido`) | Contenido de la carpeta |
| `attributes` | objeto libre | No | Datos propios de un proyecto que no entran en los campos comunes |

`path` en `files` es relativo a la carpeta del artefacto, con `/` como separador, sin `..` y nunca absoluto.

## Campos según el tipo

| Tipo | `scenario` | `rule` (`kind`, `path`, `variation`) | `variant` |
|---|---|---|---|
| `declarative.event_log` | No | No | No |
| `declarative.rules` | No | **Sí** | No |
| `declarative.embeddings` | No | No | No |
| `declarative.model_package` | No | No | No |
| `declarative.optimization_results` | No | No | No |
| `declarative.generated_log` | No | **Sí** | **Sí** |
| `declarative.prediction_diagnostics` | No | **Sí** | **Sí** |
| `declarative.simod_config` | **Sí** | No | No |
| `declarative.simulation_model` | **Sí** | No | No |
| `declarative.merged_model` | No | **Sí** | No |
| `declarative.bimp_model` | No | **Sí** | No |
| `declarative.simulation_result` | No | **Sí** | No |
| `example.*` | No | No | No |

- `scenario`: `AS-IS` o `TO-BE`.
- `rule.kind`: tipo de regla (en la línea base, `directly`); `rule.path`: la regla tal como está escrita; `rule.variation`: la variación (en la línea base, `=1`).
- Un campo marcado "No" no debe aparecer en ese tipo.

## Reglas de validación al guardar

1. `type` existe en el catálogo.
2. `status` es uno de los tres valores permitidos; con `completo`, `files` no está vacía.
3. Los identificadores respetan el formato de `identifiers.md`.
4. Cada referencia de `depends_on` existe en el registro. **Puede apuntar a otra corrida**: un modelo entrenado una vez se reutiliza en varias corridas.
5. Los campos obligatorios del tipo están presentes y los que no aplican, ausentes.
6. `created_at` está en UTC.
7. Las rutas de `files` son relativas y los hashes coinciden con los bytes guardados.
8. Primero se guardan los bytes y al final el metadato: un artefacto sin metadato no existe.
9. Después de guardar, solo `status` y `status_reason` pueden cambiar; todo lo demás es inmutable.

La lista de tipos válidos también debe existir en un archivo legible por máquina junto al esquema, y debe coincidir con `artifact-catalog.md`. Los tipos de un proyecto nuevo se agregan allí con su prefijo.

## Ejemplo

Log generado de la línea base:

```json
{
  "schema_version": "0",
  "artifact_id": "art_20261125T150210Z_0b1c2d3e",
  "run_id": "run_20261125T143000Z_a1b2c3d4",
  "task_id": "task_20261125T150005Z_9f8e7d6c",
  "producer": "predictor",
  "type": "declarative.generated_log",
  "status": "completo",
  "created_at": "2026-11-25T15:02:10Z",
  "log_name": "PurchasingExample",
  "rule": {
    "kind": "directly",
    "path": "Send Request for Quotation to Supplier >> Analyze Request for Quotation",
    "variation": "=1"
  },
  "variant": "Rules Based Random Choice",
  "depends_on": [
    { "run_id": "run_20261122T213000Z_11223344", "artifact_id": "art_20261122T213501Z_55667788" }
  ],
  "files": [
    { "path": "PurchasingExample.csv", "size_bytes": 0, "sha256": "…" },
    { "path": "PurchasingExample.xes", "size_bytes": 0, "sha256": "…" }
  ]
}
```
