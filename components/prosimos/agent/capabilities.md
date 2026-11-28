# Componente: Prosimos

**Propósito:** simular el modelo TO-BE fusionado y producir un log y estadísticas de simulación.
**Tarea:** `prosimos.simular`
**Herramienta:** `poetry run prosimos start-simulation`, ejecutado como subproceso dentro del contenedor.

## Entradas
- `modelo`: `declarative.simulation_model` del escenario TO-BE (se usa su `.bpmn`; si hay uno solo o `attributes.bpmn_file` lo indica).
- `fusionado`: `declarative.merged_model`, con exactamente un `.json`.

## Parámetros (defecto)
- `total_cases` (20): número de casos a simular.
- `timeout_segundos` (1800): tiempo máximo de Prosimos.
- `conservar_parcial` (true): registrar como parcial lo producido si Prosimos falla.

## Salidas
- `resultado`: `declarative.simulation_result` con `<modelo>_prosimos_log.csv`, `<modelo>_prosimos_stats.csv` y, si Prosimos lo genera, `simulation_warnings.txt`. Hereda `rule` del modelo fusionado; `attributes` lleva `tool`, `model_name` y `total_cases`.

## Precondiciones
- El modelo es del escenario TO-BE y trae un solo `.bpmn`; el fusionado trae un solo `.json` válido.
- `total_cases` es al menos 1; existe el comando de Prosimos y su directorio de trabajo.

## Comportamiento ante fallos
- Código distinto de 0: `fallida` (`prosimos_failed`) con el final de su salida; evidencia `parcial` con `prosimos.log`.
- Código 0 sin el log o sin las estadísticas: `fallida` (`missing_output`); si están vacíos, `empty_output`.
- Supera el tiempo límite: `fallida` (`timeout`).

## Despliegue
- **Versión del contrato:** v0.
- **Imagen:** parte de `nokal/simod` (misma base que Simod); ejecuta Prosimos como subproceso, sin Docker dentro de Docker.
- **Toma de `legacy/`:** nada; solo la forma de invocar a Prosimos.
- **Variables:** `ORQ_PROSIMOS_HOME` (`/usr/src/Simod`) y `ORQ_PROSIMOS_COMMAND` (`poetry run prosimos`).
- **Recursos:** 1 tarea simultánea. Corre como root (usuario de la imagen base).