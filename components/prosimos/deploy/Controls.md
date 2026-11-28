## Prueba de Control de Simod en PowerShell

### Iniciar
```
$env:PYTHONPATH = (Get-Location).Path
function dc  { docker compose -f infra/local/docker-compose.yml @args }
function orq { python -m shared.runtime.examples.client @args }
function J   { $input | Out-String | ConvertFrom-Json }

$PR = "http://127.0.0.1:8004"
dc up --build -d prosimos
dc ps prosimos
orq salud $PR
orq capacidades $PR
```

Para tener un modelo TO-BE y un fusionado coherentes entre sí uso los del baseline:

```
$tobe = Get-ChildItem baseline_v0\data\3.bps_tobe\PurchasingExample -Directory | Where-Object { Test-Path "$($_.FullName)\best_result\PurchasingExample_merged.json" } | Select-Object -First 1

$best = "$($tobe.FullName)\best_result"

dc exec prosimos mkdir -p /tmp/in/model /tmp/in/merged
dc cp "$best\PurchasingExample.bpmn" prosimos:/tmp/in/model/
dc cp "$best\PurchasingExample_merged.json" prosimos:/tmp/in/merged/

$modelo = dc exec prosimos python -m shared.data_access.ingest --type declarative.simulation_model --log-name PurchasingExample --scenario TO-BE --source /tmp/in/model | J

$fus = dc exec prosimos python -m shared.data_access.ingest --run $modelo.run_id --type declarative.merged_model --log-name PurchasingExample --rule-kind directly --rule-path "Send Request for Quotation to Supplier >> Analyze Request for Quotation" --rule-variation "=1" --source /tmp/in/merged | J

$r = orq enviar $PR prosimos.simular --run $modelo.run_id --input "modelo=$($modelo.run_id):$($modelo.artifact_id)" --input "fusionado=$($fus.run_id):$($fus.artifact_id)" --timeout 900 | J

$r.status; $r.error
$r.progress | ForEach-Object { $_.message }
$res = $r.outputs.resultado
dc exec prosimos ls "/data/store/$($res.run_id)/artifacts/$($res.artifact_id)/data"
```

Esperado: exitosa y tres archivos (PurchasingExample_prosimos_log.csv, _prosimos_stats.csv y simulation_warnings.txt), como en la carpeta 4.simulation_results. Para compararlos con la línea base:

```
dc cp "prosimos:/data/store/$($res.run_id)/artifacts/$($res.artifact_id)/data" .\prosimos_out
(Get-Content .\prosimos_out\simulation_warnings.txt).Count
(Get-Content "baseline_v0\data\4.simulation_results\PurchasingExample\*\simulation_warnings.txt").Count
```

Los dos conteos deberían coincidir, porque la línea base ya mostró que los avisos son idénticos entre ejecuciones con la misma entrada. Los valores del log y de las estadísticas pueden variar, porque la simulación es aleatoria.

Dos pruebas más, rápidas:
```
$r2 = orq enviar $PR prosimos.simular --run $modelo.run_id --input "modelo=$($modelo.run_id):$($modelo.artifact_id)" --input "fusionado=$($fus.run_id):$($fus.artifact_id)" --param total_cases=5 | J

$r2.status
dc exec -w /usr/src/Simod prosimos poetry run prosimos start-simulation --help
```

### Terminal
```
dc down
dc down -v
```
