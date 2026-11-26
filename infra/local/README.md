# Composición local

Levanta los dos servicios de ejemplo (`shared/runtime/examples/`) como contenedores separados que comparten solo un volumen con el almacén de artefactos. Es el cierre del paso 6: dos componentes en entornos distintos que se comunican por el contrato.

| Servicio | Puerto en tu equipo | Comando dentro del contenedor |
|---|---|---|
| `producer` | `127.0.0.1:8001` | `python -m shared.runtime.examples.producer` |
| `consumer` | `127.0.0.1:8002` | `python -m shared.runtime.examples.consumer` |

Los puertos solo escuchan en `127.0.0.1`. Dentro del contenedor, el servicio escucha en `0.0.0.0:8000`.

## Requisitos

Docker con Compose y BuildKit (el valor por defecto en las versiones recientes de Docker Desktop).

## Uso, desde la raíz del repo

```
docker compose -f infra/local/docker-compose.yml up --build -d
docker compose -f infra/local/docker-compose.yml ps
```

`ps` debe mostrar los dos servicios como `healthy` (la comprobación consulta `/health` cada 5 s). La primera construcción descarga la imagen base.

El cliente se usa desde tu equipo, igual que en `shared/runtime/examples/README.md`, apuntando a los puertos 8001 y 8002. No hace falta `ORQ_STORE_PATH`: el almacén vive en el volumen. Solo necesita `PYTHONPATH` apuntando a la raíz del repo.

```
python -m shared.runtime.examples.client salud http://127.0.0.1:8001
python -m shared.runtime.examples.client enviar http://127.0.0.1:8001 producer.generar --param text="hola desde un contenedor"
```

Para parar y limpiar:

```
docker compose -f infra/local/docker-compose.yml down        # conserva el almacén
docker compose -f infra/local/docker-compose.yml down -v     # borra también el volumen
```

## Los siete controles, ahora con contenedores

Se repiten los de `shared/runtime/examples/README.md`, con estas diferencias.

1. **Intercambio por referencia.** Ahora son dos contenedores que solo comparten el volumen: el escenario real del paso 6.
2. **Fallo forzado, 3. salida ausente, 4. precondiciones y 5. límite 1.** Iguales.
6. **Reinicio.** Envía `producer.generar` con `--no-wait --param sleep=60` y mata el contenedor sin avisarle:

   ```
   docker compose -f infra/local/docker-compose.yml kill producer
   docker compose -f infra/local/docker-compose.yml up -d producer
   ```

   Consulta la tarea: `fallida` con `interrupted`. Las tareas anteriores siguen consultables porque el volumen conserva su estado.

   Para ver la parada ordenada, usa `docker compose -f infra/local/docker-compose.yml stop producer` mientras corre una tarea larga: espera a que termine, hasta `ORQ_STOP_GRACE` (30 s por defecto), y si se agota, el contenedor es terminado y la tarea queda `interrupted`.
7. **Sin rutas.** Filtra las respuestas por `/data/store`: no debe haber coincidencias. (Aquí no hay barras invertidas que se dupliquen.)

Para mirar el almacén por dentro:

```
docker compose -f infra/local/docker-compose.yml exec producer ls /data/store
```

## Variables

| Variable | Defecto | Efecto |
|---|---|---|
| `PYTHON_VERSION` | `3.9` | Versión de Python de la imagen. Prueba `3.11` (la de la imagen de Simod) para confirmar que `shared/` funciona en ambas |
| `ORQ_STOP_GRACE` | `30s` | Tiempo que Docker espera antes de terminar el contenedor a la fuerza |

Ejemplo: `$env:PYTHON_VERSION = "3.11"; docker compose -f infra/local/docker-compose.yml up --build -d`.

## Decisiones de esta composición

- **El almacén es un volumen con nombre, no una carpeta de Windows montada.** `crear_tarea` usa enlaces duros para la creación exclusiva, y un montaje de carpeta de Windows podría no soportarlos.
- **Los contenedores corren sin privilegios** (usuario `app`). La carpeta del almacén se crea con ese dueño en la imagen para que el volumen herede los permisos.
- **Solo `shared/` entra al contexto de construcción**, mediante `Dockerfile.dockerignore`. Si al construir ves que se envían cientos de MB de contexto, BuildKit no está activo y ese archivo se está ignorando: actívalo con `$env:DOCKER_BUILDKIT = "1"`.
- **Python 3.9 ya no recibe actualizaciones de seguridad.** Aquí sirve para comprobar el mínimo declarado en D15; las imágenes de los componentes reales seguirán el entorno de cada herramienta.

## Qué queda para los componentes reales

- Cada componente tendrá su propia imagen en `components/<x>/deploy/`, partiendo de la imagen de su herramienta (`nokal/simod`, Java 8, TensorFlow), y se agregará a una composición como esta.
- `ORQ_STOP_GRACE` deberá ser mucho mayor para el entrenamiento (más de 15 minutos por corrida), o se aceptará que una parada lo marque `interrupted`.
- Composiciones para otros entornos, cuando haya componentes en máquinas distintas, vivirán en `infra/`.
