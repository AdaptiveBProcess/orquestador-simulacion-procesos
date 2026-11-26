# Componente: BIMP

**Propósito:** simular el modelo con BIMP (simulador QBP en Java) y producir un log de simulación.
**Tarea:** `bimp.simular`
**Código original que envuelve:** `bimp_parser.embed_qbp_simulation` (paso "embed simulation") y `run_bimp_docker`, con el jar `GenerativeLSTM/external_tools/bimp/qbp-simulator-engine.jar`.

## Entradas
- `declarative.simulation_model` escenario TO-BE (BPMN).
- `declarative.merged_model`.

## Pasos internos
1. Incrusta los parámetros de simulación en el BPMN: produce `declarative.bimp_model` (`*_bimp_version.bpmn`).
2. Ejecuta el simulador en un contenedor Java 8.

## Parámetros
- Ninguno por ahora.

## Salidas
- `declarative.bimp_model`.
- `declarative.simulation_result` (`*_bimp_log.csv`).

## Precondiciones
- Las rutas que ve el contenedor las define el contrato (rutas Linux dentro del contenedor), no el sistema anfitrión.

## Recursos
- Docker con la imagen `java8-xvfb` (base `eclipse-temurin:8-jdk-jammy`). El jar viene del submódulo (`external_tools/`, unos 310 MB en total).

## Notas de la línea base: fallo conocido
- El contenedor recibió una ruta de Windows (barras invertidas, relativa) y respondió "does not exist"; el código imprimió "successfully executed" porque Java devolvió 0, y no se generó `*_bimp_log.csv`.
- Al extraer BIMP, el éxito se verifica por la existencia de `*_bimp_log.csv`.

## Despliegue
- **Versión del contrato:** v0.
- **Imagen:** parte de `eclipse-temurin:8-jdk-jammy` con Xvfb (construida a partir de `docs/example/java_docker_image` del repo original).
- **Toma de `legacy/`:** el jar `GenerativeLSTM/external_tools/bimp/qbp-simulator-engine.jar` (solo ese archivo) y la lógica de `bimp_parser`.
- **Parches:** ninguno.
- **Nota:** las rutas dentro del contenedor las define el contrato, lo que debería eliminar el fallo de la línea base.
- La imagen no trae Python; se instalará para el cascarón (paso 7).
