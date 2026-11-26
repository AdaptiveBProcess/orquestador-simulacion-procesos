# Cascarón de servicio (runtime)

Pieza genérica que cada componente reutiliza para funcionar como servicio. El adaptador del componente declara **qué** hace (entradas, parámetros, salidas y la función que trabaja); el runtime hace siempre lo mismo alrededor:

1. Recibe la tarea según `shared/contracts/task-contract.md`.
2. La valida y la registra.
3. La ejecuta, con un límite de tareas simultáneas.
4. Verifica las salidas declaradas, las registra y responde.

Este documento cubre el motor (6.5). La interfaz HTTP que lo expone está en HTTP.md. No importa nada de `components/` ni de `legacy/`; solo usa la interfaz `ArtifactStore` de `shared/data_access`.

## Cómo se describe un componente

`ComponentSpec(name, tasks, max_concurrent=1, contract_version="v0")`, con una `TaskSpec` por tarea:

| Campo | Contenido |
|---|---|
| `execute(ctx)` | Hace el trabajo y devuelve `{nombre_de_salida: {...}}` |
| `inputs` | `InputSpec(type, required, allow_partial)` por entrada |
| `params` | `ParamSpec(kind, default, required, choices)` por parámetro; los defectos quedan declarados |
| `outputs` | `OutputSpec(type, required, required_files)`; `required_files` son patrones glob que deben tener al menos un archivo |
| `preconditions(ctx)` | Opcional; devuelve una lista de problemas de contenido (por ejemplo, "el log tiene muy pocos casos") |

La tarea se invoca como `<componente>.<tarea>` (por ejemplo, `predictor.generar_log`).

`ctx` ofrece `inputs` (cada una con `ref`, `path` de la carpeta materializada y `metadata`), `params` efectivos, `output_dir(nombre)` para dejar las salidas y `report(mensaje)` para avisar el avance.

Cada salida devuelta puede traer `source_dir` (por defecto, su `output_dir`), `status`, `status_reason`, `log_name`, `scenario`, `rule`, `variant`, `depends_on` y `attributes`. Si no se indica `depends_on`, se registran como dependencias todas las entradas de la tarea.

## Flujo de una tarea

1. **Recepción (`submit`).** Rechaza con excepción una solicitud sin identificadores válidos. Si el `task_id` ya existe con la misma solicitud, devuelve la tarea existente sin ejecutarla otra vez; con otra solicitud u otra corrida, lanza `TaskConflict`.
2. **Validación estructural**, sin ejecutar nada: tarea conocida, entradas presentes, existentes, del tipo declarado y completas (o parciales si `allow_partial`), parámetros conocidos, con tipo y valores permitidos, y `retry_of` válido. Si falla, la tarea se registra directamente como `fallida` (etapa `validacion`).
3. **En cola.** El registro se persiste y la tarea espera su turno.
4. **Entradas.** Se copian a la carpeta de trabajo de la tarea (`data_access.obtener`).
5. **Precondiciones de contenido.** Si fallan, la tarea termina `fallida` sin llamar a `execute`.
6. **Ejecución.** Una excepción se convierte en resultado `fallida`; el servicio no se cae.
7. **Verificación y registro de salidas.** El código de retorno no cuenta: cada salida declarada debe existir, tener archivos y cumplir `required_files`.
8. **Cierre.** Se persiste el estado final, y la carpeta de trabajo se borra si terminó bien o se conserva si falló.

## Estados y errores

| Estado | Cuándo |
|---|---|
| `en_cola`, `en_ejecucion` | Esperando turno / ejecutándose |
| `exitosa` | Todas las salidas requeridas existen y están completas |
| `parcial` | Todas las requeridas existen, pero el adaptador declaró alguna como parcial |
| `fallida` | Cualquier otro caso: validación, precondición, excepción, salida requerida ausente o inutilizable |

Los artefactos de una tarea fallida se registran igualmente, con su estado: con archivos, `parcial`; sin archivos, `fallido`. Una salida requerida que nunca se devolvió no genera artefacto.

`error` lleva `code`, `message`, `stage` (`validacion`, `entradas`, `precondiciones`, `ejecucion`, `salidas`, `interno`) y `retryable`. Códigos: `unknown_task`, `unknown_input`, `missing_input`, `invalid_input`, `input_not_found`, `input_unavailable`, `wrong_input_type`, `input_not_ready`, `unknown_param`, `missing_param`, `invalid_param`, `invalid_retry_of`, `precondition_failed`, `precondition_error`, `execution_error`, `missing_output`, `invalid_output`, `interrupted`, `internal_error`, más los de `data_access` (`integrity_error`, `backend_unavailable`…) y los que un adaptador defina con `TaskFailure(code, message, retryable, outputs)`.

## Registro de la tarea

Se guarda en `tasks/<task_id>.json` (vía `data_access`) con: ids, `component`, `task`, `request`, `effective_params`, `status`, `outputs` (nombre -> referencia), `error`, `warnings`, `progress` (últimos 50 mensajes), `created_at`, `started_at`, `finished_at` y `duration_seconds`. No contiene rutas del almacén; en los mensajes de error se sustituye la carpeta de trabajo por `<trabajo>`.

## Reinicio

Al arrancar (`start`), el runtime revisa las tareas de su componente. Las que estaban `en_ejecucion` pasan a `fallida` con código `interrupted` y `retryable`. Las que estaban `en_cola` se vuelven a encolar.

## Límites

- Una sola instancia del runtime por componente: la recuperación y la creación exclusiva de tareas no coordinan réplicas.
- Los trabajadores son hilos: el trabajo pesado o con memoria propia (TensorFlow, programas externos) lo lanza el adaptador.
- `max_concurrent` limita las tareas simultáneas de todo el componente (1 por defecto en trainer y predictor).
- Sin autenticación.
- Los avisos (`warnings`) por ahora solo registran salidas opcionales que quedaron parciales o fallidas.
