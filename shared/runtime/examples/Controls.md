## Instrucciones de Controles para el Ejemplo en PowerShell
### Preparación
```
$env:PYTHONPATH = (Get-Location).Path
function dc  { docker compose -f infra/local/docker-compose.yml @args }
function cli { python -m shared.runtime.examples.client @args }
function J   { $input | Out-String | ConvertFrom-Json }
function Ref($o) { "nota=$($o.run_id):$($o.artifact_id)" }
$P = "http://127.0.0.1:8001"; $Q = "http://127.0.0.1:8002"

dc up --build -d
dc ps
```

### Control 1: intercambio por referencia entre contenedores
```
$p1 = cli enviar $P producer.generar --param text="hola mundo desde un contenedor" | J
$p1.status                                   # exitosa
$nota = $p1.outputs.nota
$c1 = cli enviar $Q consumer.informar --run $nota.run_id --input (Ref $nota) | J
$c1.status                                   # exitosa
$inf = $c1.outputs.informe
dc exec consumer cat "/data/store/$($inf.run_id)/artifacts/$($inf.artifact_id)/data/report.txt"
dc exec consumer cat "/data/store/$($inf.run_id)/artifacts/$($inf.artifact_id)/metadata.json" | Select-String -Context 0,4 "depends_on"
```

Esperado: el informe dice caracteres: 30 y palabras: 5, y depends_on muestra el artifact_id de la nota.

### Control 2: un fallo llega como resultado y el servicio sigue
```
$f1 = cli enviar $P producer.generar --param mode=fallo | J
$f1.status; $f1.error.code                   # fallida; execution_error
$f2 = cli enviar $P producer.generar --param mode=fallo_parcial | J
$f2.status; $f2.error.code                   # fallida; fallo_forzado
dc exec producer cat "/data/store/$($f2.run_id)/artifacts/$($f2.outputs.nota.artifact_id)/metadata.json" | Select-String '"status"'
                                             # "status": "parcial"
(cli enviar $P producer.generar | J).status  # exitosa
cli salud $P                                 # status ok
```

### Control 3: terminar "bien" sin la salida declarada es un fallo
```
$s1 = cli enviar $P producer.generar --param mode=sin_salida | J
$s1.status; $s1.error.code                   # fallida; missing_output
dc exec producer cat "/data/store/$($s1.run_id)/artifacts/$($s1.outputs.nota.artifact_id)/metadata.json" | Select-String '"status"'
                                             # "status": "fallido"
$s2 = cli enviar $Q consumer.informar --run $nota.run_id --input (Ref $nota) --param mode=sin_salida | J
$s2.status; $s2.error.code                   # fallida; missing_output
```


### Control 4: una precondición incumplida se rechaza antes de ejecutar
```
$n = cli enviar $P producer.generar --param text=ab | J
$nc = $n.outputs.nota
$p4 = cli enviar $Q consumer.informar --run $nc.run_id --input (Ref $nc) --param min_caracteres=10 | J
$p4.status; $p4.error.code; $p4.error.stage # fallida; precondition_failed; precondiciones
$p4.progress.Count                           # 0: nunca llegó a ejecutarse

$pa = cli enviar $P producer.generar --param mode=parcial | J
$pa.status                                   # parcial
$pc = $pa.outputs.nota
$p5 = cli enviar $Q consumer.informar --run $pc.run_id --input (Ref $pc) | J
$p5.error.code; $p5.error.stage              # input_not_ready; validacion
```


### Control 5: con límite 1, la segunda tarea espera
```
$a = cli enviar $P producer.generar --no-wait --param sleep=15 | J
$b = cli enviar $P producer.generar --no-wait --param sleep=1 | J
(cli consultar $P $a.task_id --run $a.run_id | J).status   # en_ejecucion
(cli consultar $P $b.task_id --run $b.run_id | J).status   # en_cola
cli salud $P                                               # running: 1, queued: 1
Start-Sleep 20
(cli consultar $P $b.task_id --run $b.run_id | J).status   # exitosa
```

Ejecuta las dos primeras líneas seguidas y rápido: la primera tarea dura 15 segundos.


### Control 6: reiniciar no pierde el estado
Caída a la fuerza:
```
$t = cli enviar $P producer.generar --no-wait --param sleep=60 | J
Start-Sleep 2
dc kill producer
dc up -d producer
do { Start-Sleep 1; cli salud $P 2>$null | Out-Null } until ($LASTEXITCODE -eq 0)
$e = cli consultar $P $t.task_id --run $t.run_id | J
$e.status; $e.error.code; $e.error.retryable   # fallida; interrupted; True
(cli consultar $P $p1.task_id --run $p1.run_id | J).status   # exitosa (la del control 1 sigue ahí)
```

Parada ordenada, con una tarea en curso y otra en cola:

```
$g1 = cli enviar $P producer.generar --no-wait --param sleep=10 | J
$g2 = cli enviar $P producer.generar --no-wait --param sleep=2 | J
dc stop producer                             # tarda unos 10 s: espera a que termine la tarea en curso
dc up -d producer
do { Start-Sleep 1; cli salud $P 2>$null | Out-Null } until ($LASTEXITCODE -eq 0)
Start-Sleep 5
(cli consultar $P $g1.task_id --run $g1.run_id | J).status   # exitosa
(cli consultar $P $g2.task_id --run $g2.run_id | J).status   # exitosa: estaba en cola y se ejecutó al volver
```


### Control 7: ningún mensaje contiene rutas
Cada comando debe terminar sin ninguna línea de salida:

```
cli consultar $P $p1.task_id --run $p1.run_id | Select-String -SimpleMatch "/data/store"
cli consultar $Q $c1.task_id --run $c1.run_id | Select-String -SimpleMatch "/data/store"
cli consultar $P $f1.task_id --run $f1.run_id | Select-String -SimpleMatch "/data/store"
cli consultar $Q $p4.task_id --run $p4.run_id | Select-String -SimpleMatch "/data/store"
cli capacidades $P | Select-String -SimpleMatch "/data/store"
cli capacidades $Q | Select-String -SimpleMatch "/data/store"
```

### Finalización
```
dc down        # conserva el almacén
dc down -v     # borra también el volumen
```