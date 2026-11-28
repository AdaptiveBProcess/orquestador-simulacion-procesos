# Componente: Simod

**Propósito:** descubrir un modelo de simulación de procesos (BPMN y parámetros) a partir de un log de eventos.
**Tareas:** `simod.descubrir_asis` (log original) y `simod.descubrir_tobe` (log generado). Misma lógica; cada tarea acepta un solo tipo de log.
**Herramienta:** `poetry run simod`, ejecutado como subproceso dentro del contenedor.

## Entradas
- `log`: `declarative.event_log` (AS-IS) o `declarative.generated_log` (TO-BE). Se acepta `.csv.gz` o `.csv`; si es `.csv` se comprime.
- `config`: `declarative.simod_config`, con exactamente un archivo `.yaml`.

## Parámetros (defecto)
- `min_casos` (5): mínimo de casos del log.
- `timeout_segundos` (3600): tiempo máximo de Simod.
- `conservar_parcial` (true): registrar como parcial lo producido si Simod falla.

## Salidas
- `modelo`: `declarative.simulation_model` con el escenario de la tarea. Contiene el contenido de `best_result` en la raíz (BPMN, JSON de recursos, `canonical_model.json`, `configuration.yaml`, `runtimes.json`, métricas). `attributes` lleva `model_name`, `bpmn_file` y `json_file`.

## Precondiciones
- El log y la configuración existen y son únicos; la configuración define `common.train_log_path`.
- El log tiene al menos `min_casos` casos (la columna de caso sale de `common.log_ids.case`).
- Existe el comando de Simod y su directorio de trabajo.

## Comportamiento ante fallos
- Código distinto de 0: tarea `fallida` (`simod_failed`) con el final de la salida de Simod; la carpeta de la corrida se registra como `parcial`.
- Código 0 sin `best_result` completo: `fallida` (`missing_output`), evidencia `parcial`.
- Supera el tiempo límite: `fallida` (`timeout`).

## Despliegue
- **Versión del contrato:** v0.
- **Imagen:** parte de `nokal/simod` (Python 3.11 en `/opt/venv`, con PyYAML); ejecuta Simod como subproceso, sin Docker dentro de Docker.
- **Toma de `legacy/`:** nada; solo la forma de invocar a Simod (`--configuration`, `--output`).
- **Variables:** `ORQ_SIMOD_HOME` (`/usr/src/Simod`) y `ORQ_SIMOD_COMMAND` (`poetry run simod`).
- **Recursos:** 1 tarea simultánea. Corre como root (usuario de la imagen base).