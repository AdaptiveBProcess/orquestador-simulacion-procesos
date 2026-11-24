# Componente: Trainer

**Propósito:** entrenar el modelo LSTM de generación de trazas sobre un log de eventos.
**Tarea:** `trainer.entrenar`
**Código original que envuelve:** `GenerativeLSTM` (`model_trainer`, flujo de `dg_training.py`).

## Entradas
- `declarative.event_log`

## Parámetros (defecto de la línea base)
- Método de optimización: bayesiano. Existe un modo SLURM (`rand_hpc`) que la línea base no usó.
- Evaluaciones máximas: 10.
- `rp_sim` 0.85; `batch_size` 32; `norm_method` [max, lognorm]; `imp` 1; `epochs` 200.
- `n_size` [5, 10, 15]; `l_size` [50, 100]; `lstm_act` [selu, tanh]; `dense_act` [linear]; `optim` [Nadam].
- Formato de fecha: `%Y-%m-%dT%H:%M:%S.%f`; un timestamp por evento: no.
- Mapeo de columnas: Case ID -> caseid, Activity -> task, lifecycle:transition -> event_type, Resource -> user.

## Salidas
- `declarative.embeddings` (reutilizable como caché).
- `declarative.model_package`.
- `declarative.optimization_results`.

## Precondiciones
- El log respeta el formato de fecha y el mapeo de columnas indicados.
- Si existen embeddings de ese log, se reutilizan; si no, se entrenan.

## Recursos
- Python 3.9.18 y TensorFlow 2.20.0 (versiones de la línea base; fijarlas en el entorno).
- Tarea larga (más de 15 minutos con 10 evaluaciones): se pide de forma asíncrona.

## Notas
- El original entrena dentro del constructor y llama a `exit(1)` ante errores: el adaptador debe convertirlos en resultado `fallida`.

## Despliegue
- **Versión del contrato:** v0.
- **Imagen:** Python 3.9.18 con TensorFlow 2.20.0 y las dependencias del `environment.yml` de `GenerativeLSTM`, con versiones fijadas (incluido el paquete externo `readers`, `utils`, `analyzers`).
- **Toma de `legacy/`:** `GenerativeLSTM` (entrenamiento, embeddings, optimizador). Sin `external_tools/` ni `input_files/`, salvo que el paso 7 demuestre lo contrario.
- **Parches:** ninguno.
- **Recursos:** CPU y memoria altas; el entrenamiento tardó más de 15 minutos. Candidato a correr en un entorno distinto del resto.
