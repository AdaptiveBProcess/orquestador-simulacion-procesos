# Componente: Merger

**Propósito:** fusionar el modelo de simulación AS-IS con el TO-BE, adaptando recursos.
**Tarea:** `merger.fusionar`
**Código original que envuelve:** `adapt_json` en `support_modules/predictor_adapter.py` (remapea los identificadores de tareas por nombre).

## Entradas
- `declarative.simulation_model` escenario AS-IS.
- `declarative.simulation_model` escenario TO-BE.

## Parámetros
- Ninguno por ahora.

## Salidas
- `declarative.merged_model` (`*_merged.json`).

## Precondiciones
- Los dos modelos pertenecen al mismo log y a la misma corrida (verificable con `depends_on`).

## Recursos
- Ligero, Python puro. Hoy vive mezclado con los runners de Docker en `predictor_adapter.py`.

## Despliegue
- **Versión del contrato:** v0.
- **Imagen:** Python ligero, sin TensorFlow ni Docker.
- **Toma de `legacy/`:** la lógica de `adapt_json` de `support_modules/predictor_adapter.py`.
- **Parches:** ninguno.
