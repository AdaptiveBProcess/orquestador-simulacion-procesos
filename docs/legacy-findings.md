# Hallazgos de la revisión de los repos originales

Repos revisados: `DeclarativeProcessSimulation` (padre) y `GenerativeLSTM` (submódulo, rama `Declarative-Process`). Cada hallazgo indica su implicación de diseño.

## Estructura y flujo

El flujo es lineal en Python y usa el sistema de archivos como medio de integración: `data/0.logs … 4.simulation_results`.

| Paso del diagrama de Declarative | Dónde está |
|---|---|
| 1. Train | `dg_training.py` -> `GenerativeLSTM.model_trainer` |
| 2-3. Predict and Hallucinate | `call_predict` -> `predictor_adapter.hallucinate` |
| Extraer reglas | `traces_evaluation.extract_rules` (lee `rules.ini`) |
| 4. Generate BPS model | `generate_bps_model` -> Simod en Docker |
| 5. Simulate model | `simulate_model` -> Prosimos en Docker |
| 6. Merge AS-IS y TO-BE | `adapt_json` en `predictor_adapter` |
| 7. BIMP | `bimp_parser.embed_qbp_simulation` + `run_bimp_docker` |

La orquestación está duplicada en `dg_prediction.main` y `cli.cmd_run`.

## Hallazgos en el repo padre

| # | Hallazgo | Implicación |
|---|---|---|
| 1 | El disco es el bus de datos; `get_latest_output_folder` elige "la última corrida" por fecha | `run_id` y registro de artefactos (pasos 3 y 6) |
| 2 | `Params.py` importa `predictor_adapter`, que importa `GenerativeLSTM` (TensorFlow), solo para una función de carpetas | Componentes con dependencias propias |
| 3 | `predictor_adapter.py` mezcla runners Docker, merger y wrapper de predicción | Tres componentes distintos |
| 4 | Docker se invoca por `subprocess` desde el host con volúmenes montados | No es desplegable en entornos separados tal cual |
| 5 | Configuración dispersa: hiperparámetros fijos en `dg_training.py`; `timeformat` distinto entre entrenamiento y predicción | Parámetros explícitos por componente |
| 6 | Entornos inconsistentes: TF 2.17 (`enviroment.yml`), 2.15 (`requirements.txt`, con `pywin32`), sin versión en el submódulo | Entornos por componente con versiones fijadas |
| 7 | Manejo de errores desigual: Simod y Prosimos lanzan excepción; BIMP solo imprime | Éxito verificado contra salidas declaradas |
| 8 | Valores fijos: Prosimos simula 20 casos; `prediction.yml` con restos de otro log | Parámetros con defecto declarado |
| 9 | `models_merger`, `stochastic_model`, `log_replayer_stochastic` y `bimp_generator` no se referencian desde los flujos principales (sí `xes_writer` y `traces_evaluation`, desde el submódulo) | Posible código legado; verificar antes de descartar |

## Hallazgos en el submódulo

| # | Hallazgo | Implicación |
|---|---|---|
| 10 | Dependencia circular: el submódulo importa `support_modules.traces_evaluation` y `xes_writer` del padre. Hay tres cosas llamadas `support_modules` (carpeta del padre, carpeta del submódulo, paquete externo de Mcamargo85) | Librería de reglas compartida (D1) y regla de dependencias |
| 11 | Paquete externo (`readers`, `utils`, `analyzers`) instalado desde git sin versión fijada | Fijar versión en el entorno del componente |
| 12 | Rutas atadas al directorio de ejecución (`GenerativeLSTM/models_spec.ini`, hacks con `os.getcwd()`) | Rutas definidas por el contrato |
| 13 | El trabajo ocurre en constructores (`ModelTrainer`, `ModelPredictor`); los errores llaman a `exit(1)` y los resultados salen por disco | Adaptador que capture fallos y los convierta en resultados |
| 14 | `parms` es un diccionario mutable de unas 30 claves implícitas | Parámetros declarados por componente |
| 15 | Coordinación por sistema de archivos: los procesos cuentan `gen-*.csv` en `traces_generated` para decidir cuándo parar; al final se borran | Estado de generación fuera del disco compartido, o aislado por corrida |
| 16 | Las salidas de predicción se escriben dentro de la carpeta del modelo, mezcladas con artefactos de entrenamiento | Artefactos separados por tarea |
| 17 | Las reglas se evalúan dentro del bucle de generación, en cada paso | D1: librería en el mismo proceso |
| 18 | Solo se admite una regla por corrida | Límite a registrar en la ficha del predictor |
| 19 | `Pool(processes=cpu_count)` sin parámetro; cada proceso carga el modelo | Procesos como parámetro; memoria como recurso declarado |
| 20 | `external_tools/` pesa unos 310 MB (BIMP, SplitMiner, etc.); solo se usa el jar de BIMP | Decidir en el paso 7 |
| 21 | Entrypoints duplicados (`dg_training.py`, `dg_predictiction.py`) respecto al padre | Un único camino por componente |
| 22 | `try/except: pass` silencia errores de métricas; `XesWriter` se invoca dos veces | Registrar para el paso 7 |

## Hallazgos de la corrida de línea base

| # | Hallazgo | Implicación |
|---|---|---|
| 23 | El padre le pasaba `root_path` a un `ModelPredictor` del submódulo que no lo acepta | Contrato de versiones entre repos; ya corregido en la referencia |
| 24 | Con meta 100 % la generación se atasca (D7) | Criterio de parada explícito |
| 25 | Simod necesita `configuration_*.yaml`; sin ellos falla | Entrada obligatoria en el contrato |
| 26 | Log de 4 casos deja 0 de validación y Simod cae | Precondición verificada antes de ejecutar |
| 27 | BIMP: éxito falso con rutas de Windows (D8) | Verificar salidas, no el código de retorno |
| 28 | Identificadores con zonas horarias mezcladas; dos corridas distinguibles solo por hora | `run_id` y UTC (D9) |
| 29 | Una corrida interrumpida deja `traces_generated` sucia | Aislar y limpiar el estado de cada tarea |
