# Contrato de tarea

Mensaje común para pedirle trabajo a cualquier componente y recibir su resultado, sin importar dónde corra. No define aún el transporte (cola, HTTP u otro); eso se decide en el paso 6.

## Solicitud

| Campo | Contenido |
|---|---|
| `run_id` | Corrida a la que pertenece |
| `task` | Capacidad pedida (por ejemplo, `predictor.generar_log`) |
| `inputs` | Referencias a artefactos del catálogo, nunca rutas. una referencia es el par `(run_id, artifact_id)`; ver identifiers.md |
| `params` | Solo los que el componente declara, cada uno con su valor por defecto |
| `retry_of` | opcional: task_id de la tarea que se reintenta |

Ejemplo:

```
task: predictor.generar_log
run_id: <id de la corrida>
inputs:  paquete_modelo -> <ref>, reglas -> <ref>
params:  variante = "Rules Based Random Choice", procesos = 4
```

## Respuesta

| Campo | Contenido |
|---|---|
| `status` | `en_cola`, `en_ejecucion`, `exitosa`, `fallida` o `parcial` |
| `outputs` | Referencias a artefactos producidos (también los de una tarea fallida o parcial, con su estado) |
| `error` | Código, mensaje legible, etapa y si vale la pena reintentar |
| `warnings` | Avisos opcionales, por ejemplo los de la simulación |
| `duration` | Duración de la tarea |
| `progress` | Mensajes de avance opcionales, que el chat puede mostrar |

Las tareas largas (el entrenamiento tardó más de 15 minutos) se piden de forma asíncrona y se consulta su estado.

## Reglas

1. **El éxito se verifica contra las salidas declaradas, no contra el código de salida.** BIMP devolvió 0 sin producir resultados.
2. **Las precondiciones se validan antes de ejecutar.** Un log de 4 casos debe rechazarse con un mensaje claro, no caer dentro de Simod.
3. **Los fallos son resultados, no caídas.** Un componente responde `fallida` y sigue disponible; no mata su proceso.
4. **Un reintento es una tarea nueva** dentro de la misma corrida. Los artefactos de la anterior se conservan marcados.
5. **Las rutas no viajan.** Un componente obtiene los bytes de un artefacto por `shared/data_access` y entrega los suyos igual.
6. **Las marcas de tiempo son UTC.**

## Una corrida, varias tareas

Una corrida usa un mismo componente varias veces. Simod, por ejemplo, se ejecuta sobre el log original (escenario AS-IS) y sobre el generado (escenario TO-BE): dos tareas del mismo componente con entradas distintas. El escenario es un metadato del artefacto resultante.

## Declaración de capacidades

Cada componente publica `agent/capabilities.md` con qué sabe hacer, qué entradas y parámetros acepta, qué salidas produce, qué precondiciones exige y qué recursos necesita. El supervisor lee esas fichas para decidir a quién llamar.

## Versión del contrato

Versión actual: **v0 (borrador del paso 4)**. Cada ficha `agent/capabilities.md` declara la versión que usa. Un cambio incompatible sube la versión; los componentes migran uno a uno.

## Flujo de referencia del primer caso

```
event_log ──► Trainer ──► model_package ──► Predictor ──► generated_log
                                  rules ──►     │
event_log ──► Simod (AS-IS) ──► simulation_model (AS-IS) ─┐
generated_log ──► Simod (TO-BE) ──► simulation_model (TO-BE) ─┼► Merger ──► merged_model
                                                           │        │
                                          Prosimos ◄───────┴────────┤
                                          BIMP ◄────────────────────┘
```
