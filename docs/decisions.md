# Registro de decisiones

Formato: decisión, motivo y consecuencias. Fecha de la última revisión: 2026-11-23.

## Decididas

### D1. Las reglas declarativas son una librería compartida (opción A)
- **Decisión:** las reglas pasan a `shared/declarative_rules`, sin dependencias de TensorFlow. El predictor la usa en el mismo proceso. El componente Declarative es la cara conversacional: recibe y valida la regla y explica resultados.
- **Motivo:** en las variantes "Rules Based", cada paso de generación evalúa todas las actividades candidatas contra la regla. Por red sería inviable (opción C) y filtrar después de generar cambia el algoritmo (opción B).
- **Consecuencias:** se elimina la dependencia circular (el submódulo importaba `traces_evaluation` del repo padre). El criterio de parada de la generación viaja con esta lógica (ver D7).

### D2. La línea base es el commit actual del repo más dos parches
- **Referencia:** repo padre `DeclarativeProcessSimulation` en `1090059e09cfd4ff1f5d1c8e4d4e84cde45b821b` (22-oct-2026); submódulo `GenerativeLSTM` en `6cc041e8b6d64bd928134ec2b36b1993ae6666d2`.
- **Parches propios:** (P1) procesos del `Pool` fijados en 4; (P2) criterio de parada cuando la meta de la regla es 100 %.
- **Motivo:** sin P1 se agota la memoria en un equipo de 8 núcleos y 16 GB; sin P2 la generación con meta 100 % se detiene con 4 casos y Simod falla.
- **Consecuencias:** los parches viven como `.diff` en `docs/baseline/` y los aplica la construcción del contenedor del componente. El original no se modifica.

### D3. Catálogo de artefactos con metadatos obligatorios
- **Decisión:** ver `shared/contracts/artifact-catalog.md`. Todo artefacto lleva `run_id`, escenario cuando aplica, log, marca de tiempo UTC, estado y, si corresponde, regla y variante.
- **Motivo:** hoy esa información está codificada en nombres de carpeta, y las corridas solo se distinguen por la hora (con zonas horarias mezcladas).

### D4. Contrato de tarea único
- **Decisión:** ver `shared/contracts/task-contract.md`. El éxito se verifica contra las salidas declaradas; las precondiciones se validan antes de ejecutar; los fallos son resultados.
- **Motivo:** BIMP devuelve código 0 sin producir salidas; Simod falla dentro de su ejecución con logs pequeños; `exit(1)` mata procesos.

### D5. Un único repositorio con regla de dependencias
- **Decisión:** estructura descrita en el `README.md` raíz. El chat y la orquestación viven en `orchestrator/` dentro del mismo repo.
- **Motivo:** más sencillo de operar y suficientemente escalable. Un proyecto nuevo se agrega con componentes nuevos y tipos de artefacto con su propio prefijo.

### D6. Los proyectos originales entran como un solo submódulo
- **Decisión:** solo `DeclarativeProcessSimulation` se agrega en `legacy/`. Su submódulo `GenerativeLSTM` llega anidado, fijado en `6cc041e`.
- **Motivo:** agregar `GenerativeLSTM` también en el nivel superior lo duplicaría.

### D7. Criterio de parada de la generación con meta 100 %
- **Decisión:** se conserva el comportamiento de P2 en la línea base.
- **Motivo:** en el original, al llegar la proporción a 1 la condición `current_prop < meta` deja de cumplirse, no se agregan más trazas y la parada exige haber llegado al tamaño del log. Con meta 100 % queda atascado.
- **Pendiente:** decidir en el paso 7 dónde vive este criterio (predictor o librería de reglas).

### D8. BIMP es un fallo conocido de la línea base
- **Decisión:** se registra y no se corrige en el código original. Se resolverá al extraer BIMP como componente.
- **Motivo:** el contenedor recibe una ruta de Windows (barras invertidas, relativa) y no encuentra el BPMN; aun así el código reporta éxito.

### D9. Marcas de tiempo en UTC
- **Motivo:** los identificadores del original mezclan hora local (predictor) y UTC (Simod).

### D10. Cascarón de servicio compartido y composición en `infra/`
- **Decisión:** `shared/runtime` implementa lo que todo componente hace al recibir una tarea (validar, obtener artefactos, llamar al adaptador, verificar salidas, registrar, responder). `infra/` compone los despliegues por entorno.
- **Motivo:** sin esta pieza, cada componente reimplementaría el contrato, y nada levantaría los componentes juntos.
- **Consecuencias:** el transporte y el respaldo de datos (paso 6) quedan detrás del cascarón; el adaptador no los conoce.

### D11. La imagen del componente es la herramienta
- **Decisión:** no se usa Docker dentro de Docker. Simod y Prosimos parten de `nokal/simod` e invocan el programa directamente; BIMP parte de una imagen Java 8 con Xvfb y el jar.
- **Motivo:** el original lanza `docker run` desde el host con volúmenes montados; dentro de un contenedor eso exigiría Docker-in-Docker o montar el socket de Docker, ambos frágiles.
- **Consecuencias:** se resuelve al extraer cada componente, empezando por Simod (paso 7). Las rutas que ve cada herramienta las define el contrato.

### D12. Insumos y parches declarados por componente; `shared/` versionado
- **Decisión:** cada `deploy/` declara qué toma de `legacy/` y qué parches aplica; `shared/` se versiona y cada ficha indica la versión del contrato que usa (hoy: contrato v0, borrador del paso 4).
- **Motivo:** `legacy/` pesa mucho (`external_tools/`, unos 310 MB, de los que solo se usa un jar) y el código original asume rutas relativas al directorio de ejecución.
- **Consecuencias:** el contexto de construcción de cada imagen se limita a lo declarado. Los parches P1 y P2 solo entran en la imagen del predictor.

### D13. Transporte: HTTP con tareas asíncronas
- Decisión: cada componente expone un servicio HTTP: enviar tarea, consultar estado, ficha de capacidades y salud.
- Motivo: es lo más simple que cumple el contrato. shared/runtime lo oculta al adaptador, así que pasar a una cola más adelante no obliga a reescribir componentes.
- Runtime.shutdown acepta cancel_pending.

### D14. Respaldo de datos: disco local primero
- Decisión: shared/data_access guarda en local_store/ con la interfaz definitiva (guardar, obtener, listar, cambiar estado).
- Motivo: sirve para desarrollo y para validar el contrato; un respaldo accesible entre máquinas se agrega después sin cambiar la interfaz.

### D15. Python mínimo de shared/: 3.9. 
shared/ no puede usar sintaxis ni librerías que exijan una versión más nueva. Debe tener pocas dependencias, porque se instalará dentro de entornos de TensorFlow ya fijados.

### D16. Identificadores: 
Formato, reglas e idempotencia en shared/contracts/identifiers.md

### D17. Metadatos de artefactos
Especificación v0 en shared/contracts/artifact-metadata.md; el esquema validable se deriva de ella.

### D18. Almacenamiento local
Disposición, escritura segura y materialización por copia en shared/data_access/README.md

### D19. Validación por registro de tipos
Las reglas de metadatos se validan en código a partir de shared/contracts/artifact-types.json; sin JSON Schema por ahora.

### D20. Motor del runtime 
Modelo de tareas, estados, verificación de salidas y reinicio en shared/runtime/README.md

### D21. Interfaz HTTP
Biblioteca estándar, cuatro rutas, errores en JSON y apagado ordenado; ver shared/runtime/HTTP.md

### D22. Componentes de ejemplo
Productor y consumidor en shared/runtime/examples/, fuera de components/, para validar el contrato; los modos de fallo reproducen casos de la línea base (BIMP, Simod, caída del proceso)

### D23. Composición local
Un contenedor por servicio, volumen con nombre para el almacén (no carpeta de Windows montada), usuario sin privilegios, puertos solo en 127.0.0.1; ver infra/local/README.md

## Abiertas

| Tema | Se decide en |
|---|---|
| Transporte entre componentes (cola, HTTP u otro) | Paso 6 |
| Cómo se publica `shared/` como paquete versionado y cómo lo consume cada imagen | Paso 6 |
| Qué componentes necesitan realmente `external_tools/` (hoy solo se conoce el jar de BIMP) | Paso 7 |
| Dónde corre el entrenamiento pesado (el original tiene modo SLURM, no usado en la línea base) | Paso 6 o 7 |
| Qué hacer con `external_tools/` (unos 310 MB; solo se usa el jar de BIMP) | Paso 7 (BIMP) |
| Dónde vive el criterio de parada (D7) | Paso 7 (predictor) |
| Número de procesos del predictor como parámetro explícito | Paso 7 (predictor) |
| Versiones fijadas del entorno de TensorFlow | Paso 7 (trainer y predictor) |
| Por qué la generación produjo 76 casos y no ~101 | Paso 7 (predictor); ver `docs/baseline/BASELINE.md` |
| Autenticación entre componentes | sin ella por ahora, porque todo corre en local; se decide cuando haya componentes en máquinas distintas |
| Tiempo parada de Contenedores | Tiempo de espera de parada de los contenedores de entrenamiento (docker stop), paso 6.8 |
