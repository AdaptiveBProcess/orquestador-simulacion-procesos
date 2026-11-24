# Línea base del sistema original

Corrida de referencia de Declarative Process Simulation, ejecutada el 22-23 de noviembre de 2026 con el log de ejemplo `PurchasingExample`. Es la referencia contra la cual se comparan las extracciones del paso 7.

## 1. Identificación

| Dato | Valor |
|---|---|
| Repo padre (referencia) | `DeclarativeProcessSimulation` en `1090059e09cfd4ff1f5d1c8e4d4e84cde45b821b` (22-oct-2026) |
| Commit sobre el que se corrió | `f79efa1c49b7226c785947d187a79beedb1539c6`, inmediatamente anterior a la referencia |
| Submódulo | `GenerativeLSTM` en `6cc041e8b6d64bd928134ec2b36b1993ae6666d2` (rama `Declarative-Process`) |
| Python | 3.9.18 |
| TensorFlow | 2.20.0 (el `environment.yml` del submódulo no fija versiones; los archivos de la raíz mencionan 2.17 y 2.15) |
| Entorno | `GenerativeLSTM/environment.yml` |
| Imágenes Docker | `nokal/simod` (Simod y Prosimos); `java8-xvfb`, construida desde `docs/example/java_docker_image` con base `eclipse-temurin:8-jdk-jammy` |
| Equipo | 8 núcleos, 16 GB de RAM, Windows |

## 2. Cambios respecto al commit sobre el que se corrió

**Equivalentes a lo que ya trae la referencia** (no son parches propios): imagen base del JDK en el `Dockerfile`; eliminación de `root_path` en la llamada a `ModelPredictor` (el constructor del submódulo fijado no lo acepta); `FILENAME` de `dg_training.py` apuntando al log de ejemplo; copia de `configuration.yaml` para Simod cuando falta.

**Parches propios** (se guardan como `.diff` en esta carpeta):

| ID | Archivo | Cambio | Efecto |
|---|---|---|---|
| P1 | `GenerativeLSTM/model_prediction/event_log_predictor.py` | `Pool(processes=cpu_count)` pasa a `Pool(processes=4)` en los dos lugares donde se crea | Operativo: evita agotar la memoria. Con 8 procesos se cayó el equipo |
| P2 | mismo archivo, criterio de parada | Con meta de regla = 100 %, sigue agregando trazas que cumplen hasta alcanzar el tamaño previsto del log | Cambia el comportamiento. Corrige un defecto del original (ver `decisions.md`, D7) |

La versión de referencia para comparar es la que incluye P1 y P2.

## 3. Entrada y configuración

- **Log:** `docs/example/PurchasingExample.csv` del repo.
- **Regla (`rules.ini`):** `path = Send Request for Quotation to Supplier >> Analyze Request for Quotation`; `variation = =1` (meta de cumplimiento del 100 %); tipo de regla "directly".
- **Configuración de Simod:** `configuration_original.yaml` y `configuration_generated.yaml` son copias sin cambios de `docs/example/configuration.yaml`.
- **Entrenamiento:** optimización bayesiana, 10 evaluaciones (valores por defecto del repo). Hiperparámetros fijos en `dg_training.py`:

```
rp_sim 0.85 | batch_size 32 | norm_method [max, lognorm] | imp 1 | epochs 200
n_size [5, 10, 15] | l_size [50, 100] | lstm_act [selu, tanh]
dense_act [linear] | optim [Nadam]
timeformat '%Y-%m-%dT%H:%M:%S.%f' | one_timestamp False
columnas: Case ID->caseid, Activity->task, lifecycle:transition->event_type, Resource->user
```

- **Tiempo de entrenamiento:** no medido; más de 15 minutos.
- **Predicción:** variante "Rules Based Random Choice", una repetición (valores por defecto de la CLI).

## 4. Resultado por etapa

| Etapa | Estado | Evidencia |
|---|---|---|
| Entrenamiento | Completo | Matrices `.emb`, modelo `.h5`, `model_parameters.json`, `*_ASIS.csv`, `test_log.csv`, `OP_*.csv` |
| Generación con la regla | Completo | Log generado en `.csv`, `.csv.gz` y `.xes` |
| Simod AS-IS | Completo | `best_result` con BPMN y JSON |
| Simod TO-BE | Completo en la 2.ª corrida | La 1.ª quedó con `best_result` vacío |
| Merger | Completo | `*_merged.json` |
| Prosimos | Completo | Log, estadísticas y `simulation_warnings.txt` |
| BIMP | **Falla, reportada como éxito** | `*_bimp_version.bpmn` existe, pero no se generó `*_bimp_log.csv` |

## 5. Cifras

- Log generado: 1.764 filas y 76 casos únicos (unos 23 eventos por caso). Los 76 cumplen la regla (cumplimiento 100 %).
- Se esperaban unos 101 casos. **Observación abierta:** el predictor intenta generar un número fijo de trazas (`num_cases`) y solo conserva las que cumplen la regla; con meta 100 % el total final depende de cuántas cumplan. Es una hipótesis leída en el código, no verificada. No bloquea la línea base.
- Prosimos simula 20 casos (valor fijo en el código).

## 6. Avisos de simulación (`simulation_warnings.txt`)

- 25 avisos por condiciones faltantes en gateways.
- 40 avisos por tareas o flujos usados más de lo esperado. El mayor: "Deliver Goods Services", con 219 apariciones en 20 casos (1095 %).
- El archivo de una repetición posterior y el de esta línea base son idénticos: al menos los avisos son reproducibles con la misma entrada.

## 7. Corridas y desfase horario

La carpeta del modelo usa hora local; las carpetas de Simod usan UTC (diferencia de exactamente 5 horas). El archivo `SE_*` del modelo marca 22:57:23 (local) y el Simod AS-IS exitoso, 03:57:37 (UTC), unos 14 segundos después.

| Corrida | Simod AS-IS | Simod TO-BE | Resultado |
|---|---|---|---|
| 1 | `20261123_033947_…` | `20261123_034128_…` | Fallida: TO-BE con `best_result` vacío. Coincide con el log de 4 casos que dejó 0 casos de validación |
| 2 (oficial) | `20261123_035737_…` | `20261123_035921_…` | Completa |

Las carpetas de la corrida 1 se conservan como evidencia en `_failed_runs/`, fuera de la línea base.

## 8. Salvedades conocidas

- **BIMP:** el contenedor recibe una ruta con barras invertidas de Windows, relativa a la carpeta montada, y responde "does not exist". El código imprime "successfully executed" porque Java devuelve código 0. Hipótesis sin probar; se resuelve al extraer BIMP.
- **Simod:** con un log de 4 casos, la partición 80/20 deja 0 casos de validación y falla.
- **Predictor y memoria:** con 8 procesos el equipo se queda sin memoria.
- **Trazas residuales:** una corrida interrumpida deja `gen-*.csv` en `traces_generated`, que contaminan la siguiente. Hay que borrarlos antes de repetir.

## 9. Criterios para comparar después de cada extracción

1. Mismos tipos de artefacto producidos por etapa.
2. Cumplimiento de la regla del 100 % en el log generado.
3. Número de casos del mismo orden (la generación es aleatoria; no se espera igualdad exacta).
4. Avisos de simulación del mismo tipo.
5. BIMP: hasta extraerlo, se espera el mismo fallo; después, un `*_bimp_log.csv` real.

## 10. Archivos que acompañan esta ficha

Colócalos en esta carpeta, fuera del control de versiones los pesados:

- `baseline_tree.txt`: listado del árbol de `baseline_v0/` (sí se versiona).
- `P1-P2.diff`: los parches propios, separados del resto (sí se versiona).
- `baseline_v0/` con los datos reales (modelos, logs, resultados): no se versiona.
