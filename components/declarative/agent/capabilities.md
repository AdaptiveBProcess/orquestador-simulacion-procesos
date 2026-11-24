# Componente: Declarative

**Propósito:** recibir, validar y explicar reglas declarativas. Es la cara conversacional de las reglas; la evaluación dentro de la generación vive en `shared/declarative_rules` y la usa el Predictor.
**Tareas:** `declarative.validar_regla`, `declarative.explicar_resultado`
**Código original que envuelve:** `traces_evaluation` (`extract_rules`, `evaluate_condition_list`, `GenerateStats`).

## Entradas
- Texto de la regla (en el original, `rules.ini` con `path` y `variation`).
- Actividades del modelo (están en `model_parameters.json`, dentro de `declarative.model_package`).

## Parámetros
- Tipo de regla (en la línea base: "directly").
- Variación (en la línea base: `=1`, meta de cumplimiento del 100 %; el primer carácter indica el operador).

## Salidas
- `declarative.rules` validado.
- Avisos (actividad inexistente, meta inalcanzable, etc.).

## Precondiciones
- Una sola regla por corrida (límite del original).

## Recursos
- Ligero (pandas, networkx). Sin TensorFlow.

## Regla de la línea base
`Send Request for Quotation to Supplier >> Analyze Request for Quotation`, variación `=1`.

## Despliegue
- **Versión del contrato:** v0.
- **Imagen:** Python ligero (pandas, networkx). Sin TensorFlow.
- **Toma de `legacy/`:** solo `support_modules/traces_evaluation.py` como origen de `shared/declarative_rules`; no queda como dependencia en tiempo de ejecución.
- **Parches:** ninguno.
