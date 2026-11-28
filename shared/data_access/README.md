# data_access

Única vía para leer y escribir artefactos. Ningún componente toca rutas de almacenamiento: guarda y obtiene artefactos por referencia `(run_id, artifact_id)`.

La interfaz es independiente del respaldo. El primer respaldo es **disco local**; un respaldo accesible entre máquinas se agrega después sin cambiar la interfaz ni las referencias.

Depende solo de `shared/contracts` (para validar metadatos). No importa nada de `components/` ni de `legacy/`. Python 3.9 como mínimo (D15), con la menor cantidad posible de dependencias.

## Operaciones

| Operación | Entrada | Resultado | Notas |
|---|---|---|---|
| `guardar` | `run_id`, `task_id` (ninguno si el productor es `usuario`), `producer`, `type`, `status`, `status_reason` si aplica, campos del tipo (`log_name`, `scenario`, `rule`, `variant`, `depends_on`, `attributes`), carpeta de origen | Referencia `(run_id, artifact_id)` | Genera `artifact_id` y `created_at`; calcula `files` (tamaño y hash); valida según `artifact-metadata.md` |
| `obtener` | Referencia, `task_id`, `run_id` de la tarea (por defecto, el del artefacto), verificar (sí por defecto) | Ruta de la carpeta de trabajo con los bytes, y los metadatos | Copia los bytes, no crea enlaces. Verifica los hashes |
| `leer_metadatos` | Referencia | Metadatos | No toca los bytes |
| `listar` | `run_id`, filtros opcionales (`type`, `status`, `scenario`, `producer`) | Lista de metadatos | Ignora artefactos huérfanos |
| `cambiar_estado` | Referencia, nuevo estado, razón | Metadatos actualizados | Solo `status` y `status_reason` |

## Disposición en disco

```
<raíz del almacén>/
└─ <run_id>/
   ├─ artifacts/
   │   └─ <artifact_id>/
   │       ├─ data/           contenido del artefacto (conserva nombres y subcarpetas)
   │       └─ metadata.json   se escribe al final
   ├─ tasks/                  registro de tareas (reservado; se define en 6.5)
   └─ work/
       └─ <task_id>/
           ├─ in/<artifact_id>/   entradas materializadas por `obtener`
           └─ out/<nombre>/       salidas que la tarea entrega a `guardar`
```

Los nombres son cortos a propósito (límite de rutas de Windows). La **raíz del almacén es configurable**; por defecto `local_store/` en la raíz del repo. En Windows se recomienda una ruta corta.

## Escritura segura

1. Se genera `artifact_id` y se copian los bytes a `data/`.
2. Se calculan tamaños y hashes sobre lo copiado, no sobre el origen.
3. Se valida el metadato completo.
4. Se escribe `metadata.json` en un archivo temporal y se renombra al nombre final (el renombrado es atómico en el mismo volumen).
5. **Un artefacto sin `metadata.json` no existe.** Una caída a medias deja una carpeta huérfana: se ignora al listar y se puede limpiar con un mantenimiento aparte.

`cambiar_estado` usa el mismo mecanismo: escribe el metadato nuevo en un temporal y lo renombra.

## Carpeta de trabajo de la tarea

- `obtener` copia a `work/<task_id>/in/<artifact_id>/`. El adaptador reorganiza esos archivos con la disposición que espera el código original (rutas relativas, como en `GenerativeLSTM`).
- Las salidas se dejan en `work/<task_id>/out/` y luego se pasan a `guardar`.
- Política propuesta: al terminar bien, se borra `work/<task_id>/`; si falla, se conserva para depurar.
- Dos tareas nunca comparten carpeta de trabajo (evita el problema de `traces_generated` de la línea base).

## Utilidades de la carpeta de trabajo (solo respaldo local)

| Utilidad | Qué hace |
|---|---|
| `carpeta_trabajo(run_id, task_id)` | Crea `work/<task_id>/in` y `out` y devuelve la carpeta de trabajo |
| `eliminar_trabajo(run_id, task_id)` | Borra `work/<task_id>/`; la política (borrar si termina bien, conservar si falla) la aplica el runtime |

`obtener` recibe el `run_id` de la tarea porque un artefacto de otra corrida debe materializarse en la carpeta de trabajo de la tarea, no en la de su corrida de origen.

## Registro de tareas

El runtime guarda aquí el estado de cada tarea, en `tasks/<task_id>.json`, para que sobreviva a un reinicio y para detectar solicitudes repetidas.

| Operación | Qué hace |
|---|---|
| `crear_tarea(run_id, task_id, record)` | Creación exclusiva y atómica; `ConflictError` si ya existe |
| `leer_tarea(task_id, run_id=None)` | Devuelve el registro o `None`; sin `run_id` busca en todas las corridas |
| `actualizar_tarea(record)` | Reemplaza el registro de forma atómica |
| `listar_tareas(run_id=None, component=None, states=None)` | Lista registros con filtros opcionales |

Los backends deben implementar también las dos utilidades de la carpeta de trabajo.

## Errores

Cada uno es un error con tipo propio, que el runtime convierte en un error de tarea:

| Error | Cuándo |
|---|---|
| No encontrado | La referencia no existe o es huérfana |
| Metadato inválido | Incumple `artifact-metadata.md` (lista qué reglas) |
| Integridad | Un hash no coincide al obtener |
| Conflicto | El identificador ya existe |
| Respaldo no disponible | Disco lleno, sin permisos, ruta inaccesible |

## Configuración y uso

- Raíz del almacén, en este orden: argumento `root`, variable de entorno `ORQ_STORE_PATH`, o `local_store/` bajo el directorio actual.
- Los tipos válidos y los campos que aplican a cada uno salen de `shared/contracts/artifact-types.json`, que debe coincidir con `artifact-catalog.md`.
- Uso, con la raíz del repo en `PYTHONPATH`: `from shared.data_access import LocalDiskStore`.
- Solo biblioteca estándar; sintaxis compatible con Python 3.9.
- Si `guardar` falla después de copiar, borra lo copiado; una caída dura puede dejar una carpeta huérfana, que se ignora al listar. La limpieza de huérfanos aún no está implementada.
- Cada error tiene un `code` estable (`artifact_not_found`, `invalid_metadata`, `integrity_error`, `conflict`, `backend_unavailable`).

## Alcance y límites del respaldo local

- Asume un único sistema de archivos compartido (un volumen entre contenedores en desarrollo); no sirve entre máquinas.
- Sin control de acceso: todo corre en local.
- No borra artefactos viejos.
- Varios procesos pueden escribir a la vez sin bloqueos, porque cada artefacto tiene su propia carpeta y el metadato se publica con un renombrado atómico.

## Otros respaldos

Un respaldo remoto implementa las mismas cinco operaciones. Las referencias, los metadatos y el contrato no cambian.

ingest.py: python -m shared.data_access.ingest registra una carpeta del usuario como artefacto (productor usuario) e imprime su referencia.