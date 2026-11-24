# Componente: Simod

**Propósito:** descubrir un modelo de simulación de procesos (BPMN y parámetros) a partir de un log de eventos.
**Tarea:** `simod.descubrir_modelo` (se usa dos veces por corrida: escenario AS-IS y escenario TO-BE).
**Código original que envuelve:** `generate_bps_model` (Simod en Docker, imagen `nokal/simod`).

## Entradas
- `declarative.event_log` (escenario AS-IS) o `declarative.generated_log` (escenario TO-BE).
- `declarative.simod_config`.

## Parámetros
- La configuración de Simod (`configuration_original.yaml` o `configuration_generated.yaml`). Hay un ejemplo en `docs/example/configuration.yaml` del repo original; en la línea base se usaron copias sin cambios.

## Salidas
- `declarative.simulation_model` con su escenario (AS-IS o TO-BE).

## Precondiciones
- La configuración existe (sin ella Simod falla).
- El log tiene suficientes casos para que la partición 80/20 deje casos de validación. Con 4 casos falló.
- El original entrega el log comprimido (`.csv.gz`).

## Recursos
- Docker con la imagen `nokal/simod`.

## Notas de la línea base
- Un fallo deja carpetas con `best_result` vacío: se registran como artefacto `parcial` o `fallido`.

## Despliegue
- **Versión del contrato:** v0.
- **Imagen:** parte de `nokal/simod`; el programa se invoca directamente (sin `docker run`).
- **Toma de `legacy/`:** solo la forma en que `generate_bps_model` invoca a Simod (argumentos y archivos de entrada y salida).
- **Parches:** ninguno.
