# Componentes de ejemplo

Dos servicios mínimos para probar el runtime y el contrato sin tocar ningún componente real. Cada uno corre como un proceso separado y se comunican solo por el contrato y el almacén de artefactos: es el ensayo de lo que harán dos contenedores en 6.8.

| Servicio | Tarea | Entradas | Salidas | Parámetros |
|---|---|---|---|---|
| `producer` | `producer.generar` | ninguna | `nota` (`example.note`, con `note.txt`) | `text`, `mode`, `sleep` |
| `consumer` | `consumer.informar` | `nota` (`example.note`, completa) | `informe` (`example.report`, con `report.txt`) | `min_caracteres`, `mode`, `sleep` |

Ambos tienen límite de 1 tarea simultánea.

## Modos que provocan cada comportamiento

| Servicio | `mode` | Qué provoca | Resultado esperado |
|---|---|---|---|
| producer | `normal` | Trabajo correcto | `exitosa` |
| producer | `fallo` | Una excepción tras escribir la nota | `fallida`, código `execution_error`, sin artefacto |
| producer | `fallo_parcial` | Un fallo controlado que entrega la nota a medias | `fallida`, código `fallo_forzado`, nota registrada como `parcial` |
| producer | `sin_salida` | Termina sin error y sin escribir `note.txt` (el caso de BIMP) | `fallida`, código `missing_output`, nota registrada como `fallido` |
| producer | `parcial` | Declara la nota como parcial | tarea `parcial` |
| consumer | `normal` | Trabajo correcto | `exitosa` |
| consumer | `fallo` | Una excepción | `fallida`, `execution_error` |
| consumer | `sin_salida` | Termina sin escribir `report.txt` | `fallida`, `missing_output` |

Además, `sleep` (segundos) alarga la tarea para ver la cola, y `min_caracteres` en el consumidor incumple una precondición de contenido si la nota es más corta.

## Cómo ejecutarlos (Windows, PowerShell)

Necesitas la raíz del repo en `PYTHONPATH` y un almacén compartido por los dos procesos. Usa una ruta corta (límite de rutas de Windows) y con un nombre fácil de buscar.

```
$env:PYTHONPATH = "C:\ruta\a\la\raiz\del\repo"
$env:ORQ_STORE_PATH = "C:\dev\orq_store_demo"
```

Terminal 1, el productor:

```
$env:ORQ_HTTP_PORT = "8001"; python -m shared.runtime.examples.producer
```

Terminal 2, el consumidor (con las mismas dos variables de entorno de arriba):

```
$env:ORQ_HTTP_PORT = "8002"; python -m shared.runtime.examples.consumer
```

Terminal 3, el cliente (también con `PYTHONPATH`):

```
python -m shared.runtime.examples.client salud http://127.0.0.1:8001
python -m shared.runtime.examples.client capacidades http://127.0.0.1:8002
python -m shared.runtime.examples.client enviar http://127.0.0.1:8001 producer.generar --param text="hola mundo"
```

`enviar` espera el resultado e imprime el registro de la tarea. El código de salida es 0 si terminó `exitosa` o `parcial`, y 1 en otro caso. Para encadenar, toma `run_id` y `artifact_id` de `outputs.nota` del resultado anterior:

```
python -m shared.runtime.examples.client enviar http://127.0.0.1:8002 consumer.informar --run <run_id> --input nota=<run_id>:<artifact_id>
```

Opciones útiles de `enviar`: `--param clave=valor` (repetible), `--no-wait`, `--retry-of <task_id>`, `--task-id`.

## Los siete controles del paso 6

Cada uno se puede comprobar a mano con el cliente.

1. **Intercambio por referencia entre procesos.** Genera una nota con el productor y úsala en el consumidor, como arriba. El informe sale `exitosa` y su `depends_on` apunta a la nota. Los dos procesos solo comparten el almacén.
2. **Un fallo llega como resultado y el servicio sigue.** `--param mode=fallo` y `--param mode=fallo_parcial` al productor: ambas quedan `fallida`; la segunda deja una nota `parcial` registrada. Después, una tarea normal funciona.
3. **Terminar "bien" sin la salida declarada es un fallo.** `--param mode=sin_salida`: queda `fallida` con `missing_output`.
4. **Una precondición incumplida se rechaza antes de ejecutar.** Genera la nota con `--param text=ab` y pídele al consumidor `--param min_caracteres=10`: `precondition_failed`, etapa `precondiciones`. Si le pasas una nota `parcial` (`mode=parcial`), se rechaza en la recepción con `input_not_ready`, etapa `validacion`.
5. **Con límite 1, la segunda tarea espera.** Envía dos tareas con `--no-wait --param sleep=10`; consulta la segunda: `en_cola`. `salud` muestra `running: 1` y `queued: 1`.
6. **Reiniciar no pierde el estado.** Envía una tarea con `--no-wait --param sleep=60` y termina el proceso a la fuerza:

   ```
   Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*examples.producer*' } | Select-Object ProcessId
   Stop-Process -Id <PID> -Force
   ```

   Vuelve a arrancar el productor y consulta la tarea: `fallida` con `interrupted` y `retryable: true`. Las tareas anteriores siguen consultables. (Con `Ctrl+C` el servicio termina de forma ordenada: espera a la tarea en curso y deja las que están en cola como `en_cola`, que se ejecutan al volver a arrancar.)
7. **Ningún mensaje contiene rutas.** Ejecuta cualquiera de los comandos anteriores y filtra por el nombre de tu almacén: no debe haber coincidencias.

   ```
   python -m shared.runtime.examples.client consultar http://127.0.0.1:8001 <task_id> | Select-String -SimpleMatch "orq_store_demo"
   ```

## Para qué sirven en 6.8

La composición de `infra/` levantará cada uno en su contenedor, con la misma imagen base y un volumen para el almacén. El comando de arranque es el mismo: `python -m shared.runtime.examples.producer` o `...consumer`.
