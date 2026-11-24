# Componente: Prosimos

**Propósito:** simular el modelo fusionado y producir un log y estadísticas de simulación.
**Tarea:** `prosimos.simular`
**Código original que envuelve:** `simulate_model` (Prosimos en Docker, imagen `nokal/simod`).

## Entradas
- `declarative.simulation_model` escenario TO-BE (BPMN).
- `declarative.merged_model`.

## Parámetros
- Número de casos a simular: hoy fijo en 20 en el código (debe volverse parámetro).
- Repeticiones: por confirmar al extraer el componente.

## Salidas
- `declarative.simulation_result`: `*_prosimos_log.csv`, `*_prosimos_stats.csv`, `simulation_warnings.txt`.

## Precondiciones
- Los modelos pertenecen a la misma corrida.

## Recursos
- Docker con la imagen `nokal/simod`.

## Notas de la línea base
- Avisos esperados: 25 por condiciones faltantes en gateways y 40 por tareas o flujos usados más de lo esperado (el mayor, "Deliver Goods Services", 219 apariciones en 20 casos, 1095 %). Los avisos fueron idénticos en dos ejecuciones.
- En el original, los resultados se guardan en una carpeta cuyo nombre codifica la regla (`directly__<tarea>__<tarea>`); esa información pasa a metadatos.

## Despliegue
- **Versión del contrato:** v0.
- **Imagen:** parte de `nokal/simod` (misma base que Simod); invoca Prosimos directamente.
- **Toma de `legacy/`:** solo la forma en que `simulate_model` invoca a Prosimos.
- **Parches:** ninguno.
