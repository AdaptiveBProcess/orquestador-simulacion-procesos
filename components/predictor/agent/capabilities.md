# Componente: Predictor

**Propósito:** generar un log de eventos nuevo con el modelo entrenado, guiado por una regla declarativa.
**Tarea:** `predictor.generar_log`
**Código original que envuelve:** `GenerativeLSTM` (`ModelPredictor`, `EventLogPredictor`) vía `predictor_adapter.hallucinate`.

## Entradas
- `declarative.model_package`
- `declarative.rules`

## Parámetros
- Variante de generación: "Rules Based Random Choice" (defecto de la CLI); también existen "Random Choice", "Arg Max" y otras variantes basadas en reglas.
- Número de procesos: 4 en la línea base (con 8 en un equipo de 8 núcleos y 16 GB se agotó la memoria). Debe ser un parámetro explícito.
- Tamaño previsto del log (en el original, el número de casos del log de referencia).
- Repeticiones: 1 (defecto de la CLI).

## Salidas
- `declarative.generated_log` (`.csv`, `.csv.gz`, `.xes`).
- `declarative.prediction_diagnostics` (`SE_*`, `tst_*`, `gen_*`).

## Precondiciones
- Las actividades de la regla existen en el modelo (validado por la librería de reglas).
- Una sola regla por corrida.

## Recursos
- TensorFlow; cada proceso carga el modelo, así que la memoria crece con el número de procesos.

## Notas de la línea base
- Aplica los parches P1 (procesos en 4) y P2 (criterio de parada con meta 100 %).
- Con la regla "directly" de ejemplo y meta 100 % generó 76 casos, todos conformes; se esperaban unos 101 (observación abierta).
- Usa la librería `shared/declarative_rules` (D1) dentro del mismo proceso.
- El original coordina procesos contando `gen-*.csv` en una carpeta: el estado de cada tarea debe aislarse y limpiarse.

## Despliegue
- **Versión del contrato:** v0.
- **Imagen:** la misma base que el Trainer (Python 3.9.18, TensorFlow 2.20.0).
- **Toma de `legacy/`:** `GenerativeLSTM` (`model_prediction`) y la lógica de `predictor_adapter.hallucinate`. `traces_evaluation` y `xes_writer`, que hoy viven en el repo padre, pasan a `shared/declarative_rules` y al adaptador.
- **Parches:** P1 y P2 (`docs/baseline/P1-P2.diff`).
- **Recursos:** memoria proporcional al número de procesos; con 8 procesos en 16 GB se agotó.
