# Interfaz HTTP del runtime

Capa delgada sobre `Runtime` (`shared/runtime/http_service.py`). Traduce HTTP al contrato de tarea (`shared/contracts/task-contract.md`) y los errores del runtime a códigos de estado. Solo usa la biblioteca estándar; no tiene autenticación (todo corre en local).

Todas las respuestas son JSON (`application/json; charset=utf-8`) con `Cache-Control: no-store`.

## Rutas

| Ruta | Qué hace |
|---|---|
| `POST /tasks` | Envía una tarea. El cuerpo es la solicitud del contrato |
| `GET /tasks/{task_id}` | Registro de la tarea: estado, avance, salidas, error y avisos. Admite `?run_id=` |
| `GET /capabilities` | Ficha de capacidades del componente (tareas, entradas, parámetros con defecto, salidas) |
| `GET /health` | `status`, tareas en cola y en ejecución, y límite de concurrencia |

Cualquier otro método en una ruta conocida responde `405` con la cabecera `Allow`.

## Enviar una tarea

```
POST /tasks
Content-Type: application/json

{
  "run_id":  "run_20261125T143000Z_a1b2c3d4",
  "task_id": "task_20261125T143012Z_9f8e7d6c",
  "task":    "predictor.generar_log",
  "inputs":  { "paquete_modelo": { "run_id": "...", "artifact_id": "..." } },
  "params":  { "procesos": 4 },
  "retry_of": "task_..."            (opcional)
}
```

El orquestador genera `run_id` y `task_id`. Las entradas son referencias a artefactos, nunca rutas.

| Código | Cuándo |
|---|---|
| `202` | La tarea quedó registrada y aún no termina (`en_cola` o `en_ejecucion`). Incluye la cabecera `Location: /tasks/{task_id}` |
| `200` | La tarea ya está en estado final: o no pasó la validación (`fallida`, etapa `validacion`) o es una solicitud repetida de una tarea terminada. Se devuelve el registro existente sin ejecutar de nuevo |

**Una validación fallida no es un error HTTP.** La tarea existe, con estado `fallida` y su `error`; así queda registrada y consultable.

## Consultar una tarea

`GET /tasks/{task_id}` devuelve el registro completo (ver `shared/runtime/README.md`). Se consulta periódicamente hasta que el estado sea `exitosa`, `parcial` o `fallida`. `?run_id=` evita buscar la tarea en todas las corridas.

## Errores

Siempre con esta forma:

```
{ "error": { "code": "task_conflict", "message": "el task_id ya existe con una solicitud distinta" } }
```

| Estado | `code` | Cuándo |
|---|---|---|
| 400 | `invalid_json` | El cuerpo no es JSON |
| 400 | `invalid_request` | Solicitud sin la forma del contrato, ids inválidos, campos desconocidos |
| 404 | `task_not_found` / `not_found` | La tarea no existe / ruta desconocida |
| 405 | `method_not_allowed` | Método no admitido en esa ruta |
| 409 | `task_conflict` | El `task_id` ya existe con otra solicitud o en otra corrida |
| 411 | `length_required` | Falta `Content-Length` (no se admite `Transfer-Encoding`) |
| 413 | `payload_too_large` | El cuerpo supera el máximo |
| 415 | `unsupported_media_type` | El `Content-Type` no es `application/json` |
| 500 | `internal_error`, `integrity_error` | Error inesperado (sin detalles internos) o registro dañado |
| 503 | `backend_unavailable` | El respaldo de datos no está disponible |

Los códigos de error propios de una tarea (`unknown_param`, `precondition_failed`, `missing_output`…) viajan dentro del registro de la tarea, no como errores HTTP.

## Configuración

| Variable | Defecto | Efecto |
|---|---|---|
| `ORQ_HTTP_HOST` | `127.0.0.1` | Dirección de escucha. En contenedor, la composición de `infra/` la cambia a `0.0.0.0` |
| `ORQ_HTTP_PORT` | `8000` | Puerto |
| `ORQ_HTTP_MAX_BODY` | `1048576` | Tamaño máximo del cuerpo, en bytes |

Los argumentos de `make_server(runtime, host, port, max_body)` tienen prioridad sobre las variables.

## Uso

```python
from shared.runtime import Runtime, serve
serve(Runtime(component, store))      # bloquea hasta SIGINT o SIGTERM
```

`make_server(runtime, ...)` crea el servidor sin arrancarlo, para integrarlo en otro bucle.

## Apagado

Al recibir SIGINT o SIGTERM el servicio deja de aceptar peticiones y cancela las tareas en cola, que siguen registradas como `en_cola` y se vuelven a encolar al arrancar de nuevo. La tarea en ejecución continúa hasta terminar. Si el proceso es terminado a la fuerza (por ejemplo, el tiempo de espera de `docker stop`), esa tarea queda `fallida` con código `interrupted` al volver a arrancar.

## Límites

- Una conexión por petición (HTTP/1.0): los clientes que consultan con frecuencia reabren conexión cada vez.
- Pensado para tráfico interno entre componentes, no para exponerlo a internet.
- Sin autenticación ni cifrado.
- Una sola instancia por componente.
