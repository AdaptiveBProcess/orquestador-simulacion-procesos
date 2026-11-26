# Identificadores

Definen cómo se nombran las corridas, las tareas y los artefactos. Aplica a todo el contrato (`task-contract.md`) y al catálogo (`artifact-catalog.md`).

## Formato

```
<tipo>_<AAAAMMDDTHHMMSSZ>_<sufijo>
```

| Tipo | Identifica | Ejemplo |
|---|---|---|
| `run` | Una corrida completa | `run_20261125T143000Z_a1b2c3d4` |
| `task` | Una tarea de un componente dentro de una corrida | `task_20261125T143012Z_9f8e7d6c` |
| `art` | Un artefacto | `art_20261125T143540Z_0b1c2d3e` |

- La marca de tiempo es UTC, del momento en que se genera el identificador (no del trabajo).
- El sufijo son 8 caracteres hexadecimales aleatorios.
- Solo minúsculas, dígitos y guion bajo; sin espacios ni barras.
- Longitud de unos 30 caracteres. Se mantiene corta a propósito: las rutas largas de Windows ya fallaron una vez al clonar el submódulo.

## Reglas

1. **Son opacos.** Un componente nunca interpreta un identificador; solo lo recibe y lo devuelve. La marca de tiempo sirve para ordenar a simple vista y depurar, no como dato: la fecha oficial es el metadato `created_at`.
2. **Quién los genera.** El orquestador genera `run_id` y `task_id`. `data_access` genera `art` al guardar un artefacto. Un componente nunca inventa los de otro.
3. **Nunca se reutilizan ni se modifican.** Un identificador asignado queda fijo, incluso si la tarea falla.
4. **Idempotencia.** Si llega un `task_id` que ya existe con la misma solicitud, el servicio devuelve la tarea existente y no la ejecuta de nuevo. Si llega con una solicitud distinta, la rechaza como conflicto. Así, un reintento de red no duplica trabajo y un error de programación no pasa desapercibido.
5. **Una tarea pertenece a una sola corrida.** Si un `task_id` llega con otro `run_id`, se rechaza como conflicto.
6. **Los reintentos son tareas nuevas.** Un reintento lleva un `task_id` nuevo, en la misma corrida, y el campo opcional `retry_of` con el `task_id` de la tarea que reintenta. Los artefactos de la tarea anterior se conservan con su estado.

## Referencia a un artefacto

Una referencia es el par `(run_id, artifact_id)`. Nunca es una ruta.

```
{ "run_id": "run_20261125T143000Z_a1b2c3d4",
  "artifact_id": "art_20261125T143540Z_0b1c2d3e" }
```

Llevar la corrida en la referencia permite que cualquier respaldo localice el artefacto sin buscar, tanto en disco local como en uno remoto.

## Carpetas de trabajo de una tarea

Cuando una tarea obtiene sus entradas, `data_access` las materializa en una carpeta propia de esa tarea, nombrada con su `task_id`. El adaptador entrega esa carpeta al código original. Dos tareas nunca comparten carpeta de trabajo.
