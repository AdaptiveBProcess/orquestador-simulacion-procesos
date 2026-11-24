# Orquestador de procesos

Sistema multiagente desacoplado: agentes especializados en herramientas concretas, orquestados para completar un flujo de trabajo guiado de forma conversacional.

Cada componente tiene su propio espacio de despliegue. La estrategia de datos se diseñó desde el inicio: los componentes **nunca comparten rutas, comparten referencias a artefactos**, lo que permite que corran en entornos distintos.

## Primer caso: Declarative Process Simulation

Genera ("alucina") logs de eventos con un modelo LSTM guiado por reglas declarativas y simula el proceso resultante. Pipeline original:

1. Entrenar el modelo LSTM sobre un log de eventos.
2. Generar un log nuevo que cumpla una regla declarativa.
3. Descubrir modelos de simulación con Simod (AS-IS sobre el log original, TO-BE sobre el generado).
4. Fusionar AS-IS y TO-BE.
5. Simular con Prosimos y con BIMP.

Los diagramas de arquitectura (general y de Declarative) van en `docs/architecture/`.

## Estructura

```
/
├─ orchestrator/            Chat, supervisor, manejador de servicios (paso 8)
├─ components/
│   └─ <componente>/        trainer, predictor, declarative, merger, simod, prosimos, bimp
│       ├─ agent/           ficha de capacidades (capabilities.md)
│       ├─ adapter/         traduce contrato <-> código original
│       ├─ tool/            ejecuta el código original o la herramienta
│       └─ deploy/          entorno, imagen, insumos de legacy y parches
├─ shared/
│   ├─ contracts/           catálogo de artefactos y contrato de tarea
│   ├─ data_access/         única vía para leer y escribir artefactos
│   ├─ runtime/             cascarón de servicio que reutiliza cada componente
│   └─ declarative_rules/   librería de reglas declarativas
├─ infra/                   composición de los componentes por entorno
├─ legacy/                  repos originales (submódulo), sin modificar
├─ docs/                    decisiones, hallazgos, línea base, arquitectura
└─ local_store/             bytes de desarrollo (no se versiona)
```

## Regla de dependencias

- `components/*` pueden usar `shared/*`.
- `shared/*` no importa nada de `components/` ni de `legacy/`.
- Solo `components/*/tool` toca `legacy/`.
- Los componentes no se llaman entre sí: se comunican solo mediante el contrato y los artefactos.
- `infra/` solo compone: no contiene lógica.

Esta regla existe porque el código original tenía una dependencia circular entre el repo padre y su submódulo (ver `docs/legacy-findings.md`).

## Despliegue por componente

Cada componente se construye y se despliega por separado desde su carpeta `deploy/`:

1. **La imagen del componente es la herramienta.** Se parte de la imagen que ya contiene el programa (por ejemplo `nokal/simod` o una imagen Java 8) y se invoca directamente; no se lanza `docker run` desde dentro de un contenedor.
2. **Cada `deploy/` declara qué toma de `legacy/` y qué parches aplica.** No se copia `legacy/` completo a ninguna imagen.
3. **`shared/` se versiona.** Cada componente declara en su ficha la versión del contrato que usa.

Todos los componentes se apoyan en `shared/runtime` para recibir tareas, validar, registrar artefactos y responder. Mientras el paso 6 no defina el transporte y un respaldo de datos accesible de forma remota, los componentes solo pueden correr en la misma máquina con un disco compartido.

## Cómo clonar

```
git clone --recurse-submodules <url-de-este-repo>
```

Si ya lo clonaste sin submódulos: `git submodule update --init --recursive`.

## Qué no se versiona

Datos y artefactos pesados: `local_store/`, modelos `.h5`, logs, resultados de simulación y la carpeta de la línea base con datos. Solo se versionan documentos, contratos y código.

## Documentos clave

| Documento | Para qué sirve |
|---|---|
| `docs/roadmap.md` | Plan por pasos y su estado |
| `docs/decisions.md` | Decisiones tomadas y abiertas |
| `docs/legacy-findings.md` | Hallazgos de la revisión de los repos originales |
| `docs/baseline/BASELINE.md` | Corrida de referencia del sistema original |
| `infra/README.md` | Cómo se componen los despliegues |
| `shared/contracts/artifact-catalog.md` | Qué artefactos existen y quién los produce |
| `shared/contracts/task-contract.md` | Cómo se pide trabajo a un componente |
| `components/*/agent/capabilities.md` | Qué sabe hacer cada componente |

## Convenciones

- Todas las marcas de tiempo en UTC.
- Cada ejecución lleva un `run_id` que une todas sus etapas; nunca se usa "la última carpeta".
- Los tipos de artefacto llevan prefijo de dominio (`declarative.*`) para que otros proyectos agreguen los suyos sin chocar.
