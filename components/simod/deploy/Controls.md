## Prueba de Control de Simod en PowerShell

### Iniciar
```
$env:PYTHONPATH = (Get-Location).Path
function dc  { docker compose -f infra/local/docker-compose.yml @args }
function orq { python -m shared.runtime.examples.client @args }
function J   { $input | Out-String | ConvertFrom-Json }
$S = "http://127.0.0.1:8003"

dc up --build -d simod
dc ps simod                      # healthy
orq salud $S
orq capacidades $S               # dos tareas: descubrir_asis y descubrir_tobe
```

Registrar las entradas (el primer comando crea la corrida; copia su run_id):
```
dc exec simod mkdir -p /tmp/in/log /tmp/in/cfg /tmp/in/glog
dc cp baseline_v0/data/0.logs/PurchasingExample/PurchasingExample.csv simod:/tmp/in/log/
dc cp legacy/DeclarativeProcessSimulation/docs/example/configuration.yaml simod:/tmp/in/cfg/

$log = dc exec simod python -m shared.data_access.ingest --type declarative.event_log --log-name PurchasingExample --source /tmp/in/log | J

$cfg = dc exec simod python -m shared.data_access.ingest --run $log.run_id --type declarative.simod_config --log-name PurchasingExample --scenario AS-IS --source /tmp/in/cfg | J

$log; $cfg
```

AS-IS con el Simod real (puede tardar varios minutos; el cliente espera hasta 30):
```
$r = orq enviar $S simod.descubrir_asis --run $log.run_id --input "log=$($log.run_id):$($log.artifact_id)" --input "config=$($cfg.run_id):$($cfg.artifact_id)" --timeout 1800 | J

$r.status; $r.error
$r.progress | ForEach-Object { $_.message }
$m = $r.outputs.modelo
dc exec simod cat "/data/store/$($m.run_id)/artifacts/$($m.artifact_id)/metadata.json"
dc exec simod ls "/data/store/$($m.run_id)/artifacts/$($m.artifact_id)/data"
```

Esperado: exitosa, escenario AS-IS, y en data los mismos archivos que tu baseline_v0/data/3.bps_asis/PurchasingExample/<corrida>/best_result.

TO-BE con el log generado de la corrida 2 (ajusta la variante y la regla si se cambió):
```
dc exec simod mkdir -p /tmp/in/glog
dc cp baseline_v0/data/2.hallucination_logs/PurchasingExample/PurchasingExample.csv simod:/tmp/in/glog/

$glog = dc exec simod python -m shared.data_access.ingest --run $log.run_id --type declarative.generated_log --log-name PurchasingExample --variant "Rules Based Random Choice" --rule-kind directly --rule-path "Send Request for Quotation to Supplier >> Analyze Request for Quotation" --rule-variation "=1" --source /tmp/in/glog | J

$cfg2 = dc exec simod python -m shared.data_access.ingest --run $log.run_id --type declarative.simod_config --log-name PurchasingExample --scenario TO-BE --source /tmp/in/cfg | J

$t = orq enviar $S simod.descubrir_tobe --run $log.run_id --input "log=$($glog.run_id):$($glog.artifact_id)" --input "config=$($cfg2.run_id):$($cfg2.artifact_id)" --timeout 1800 | J

$t.status; $t.error
$t.progress | ForEach-Object { $_.message }
$q = $t.outputs.modelo
dc exec simod cat "/data/store/$($q.run_id)/artifacts/$($q.artifact_id)/metadata.json"
dc exec simod ls "/data/store/$($q.run_id)/artifacts/$($q.artifact_id)/data"
```

### Terminal
```
dc down
dc down -v
```
