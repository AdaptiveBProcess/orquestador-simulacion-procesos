## Prueba de Control de Merger en PowerShell

### Iniciar
```
$env:PYTHONPATH = (Get-Location).Path
function dc  { docker compose -f infra/local/docker-compose.yml @args }
function orq { python -m shared.runtime.examples.client @args }
function J   { $input | Out-String | ConvertFrom-Json }

$PM = "http://127.0.0.1:8005"
dc up --build -d merger
dc ps merger
orq salud $PM
orq capacidades $PM
```

Para la prueba se hace uso de los modelos de la línea base, de modo que el resultado se pueda comparar con el archivo que ya generó el sistema original:

```
$asisDir = Get-ChildItem baseline_v0\data\3.bps_asis\PurchasingExample -Directory | Sort-Object Name | Select-Object -Last 1

$tobeDir = Get-ChildItem baseline_v0\data\3.bps_tobe\PurchasingExample -Directory | Sort-Object Name | Select-Object -Last 1

$asisDir.Name; $tobeDir.Name        # deben ser los de la corrida buena (..._035737_... y ..._035921_...)

dc exec merger mkdir -p /tmp/in/asis /tmp/in/tobe /tmp/in/regla
dc cp "$($asisDir.FullName)\best_result\PurchasingExample.bpmn" merger:/tmp/in/asis/
dc cp "$($asisDir.FullName)\best_result\PurchasingExample.json" merger:/tmp/in/asis/
dc cp "$($tobeDir.FullName)\best_result\PurchasingExample.bpmn" merger:/tmp/in/tobe/
dc cp "$($tobeDir.FullName)\best_result\PurchasingExample.json" merger:/tmp/in/tobe/
dc cp "baseline_v0\data\0.logs\PurchasingExample\rules.ini" merger:/tmp/in/regla/
```

Solo se copian estos archivos de cada modelo y las reglas.

```
$asis = dc exec merger python -m shared.data_access.ingest --type declarative.simulation_model --log-name PurchasingExample --scenario AS-IS --source /tmp/in/asis | J

$tobe = dc exec merger python -m shared.data_access.ingest --run $asis.run_id --type declarative.simulation_model --log-name PurchasingExample --scenario TO-BE --source /tmp/in/tobe | J

$regla = dc exec merger python -m shared.data_access.ingest --run $asis.run_id --type declarative.rules --log-name PurchasingExample --rule-kind directly --rule-path "Send Request for Quotation to Supplier >> Analyze Request for Quotation" --rule-variation "=1" --source /tmp/in/regla | J

$r = orq enviar $PM merger.fusionar --run $asis.run_id --input "asis=$($asis.run_id):$($asis.artifact_id)" --input "tobe=$($tobe.run_id):$($tobe.artifact_id)" --input "regla=$($regla.run_id):$($regla.artifact_id)" | J

$r.status; $r.error
$r.progress | ForEach-Object { $_.message }
$m = $r.outputs.fusionado
```

La comparación con el archivo del sistema original:
```
dc cp "merger:/data/store/$($m.run_id)/artifacts/$($m.artifact_id)/data/PurchasingExample_merged.json" .\merged_nuevo.json

Compare-Object (Get-Content .\merged_nuevo.json) (Get-Content "$($tobeDir.FullName)\best_result\PurchasingExample_merged.json")
```

Si no imprime nada, son idénticos. Usa Get-Content y no una comparación de bytes: el sistema original escribió el archivo en Windows (con \r\n) y el contenedor escribe \n, así que los bytes difieren aunque el contenido sea el mismo.

Validar con Prosimos:
```
$rp = orq enviar http://127.0.0.1:8004 prosimos.simular --run $asis.run_id --input "modelo=$($tobe.run_id):$($tobe.artifact_id)" --input "fusionado=$($m.run_id):$($m.artifact_id)" --timeout 900 | J

$rp.status; $rp.error
```

### Terminal
```
dc down
dc down -v
```
