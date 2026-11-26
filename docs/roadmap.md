# Plan de trabajo

Última actualización: 2026-11-23.

| Paso | Contenido | Estado |
|---|---|---|
| 1 | Decidir qué pasa con las reglas declarativas | Hecho: opción A (librería compartida) |
| 2 | Línea base del sistema original | Hecho, con salvedad: BIMP no produce resultados (`docs/baseline/BASELINE.md`) |
| 3 | Vocabulario y catálogo de artefactos | Hecho (`shared/contracts/artifact-catalog.md`) |
| 4 | Contrato de tarea | Hecho (`shared/contracts/task-contract.md`) |
| 5 | Esqueleto de carpetas y repo (incluye `shared/runtime` e `infra/`) | Hecho |
| 6 | Capa de datos mínima (respaldo local), elección del transporte, cascarón de servicio (`shared/runtime`) y composición local (`infra/`) | Hecho |
| 7 | Extraer componentes, del más simple al más pesado | Pendiente |
| 8 | Orquestación: primero sin chat, luego capa conversacional | Pendiente |

## Orden previsto del paso 7

1. Simod (aquí se elimina el uso de Docker dentro de Docker). 2. Prosimos. 3. Merger. 4. BIMP. 5. Declarative (librería de reglas más agente). 6. Predictor. 7. Trainer.

Tras cada extracción se compara contra la línea base.

## Controles por paso

- **5:** la estructura se entiende sin explicación; ninguna dependencia va al revés; un proyecto nuevo se agrega sin tocar lo existente.
- **6:** se guarda y recupera un artefacto por su referencia desde dos procesos distintos, y dos componentes de ejemplo corren como contenedores separados y se comunican mediante el contrato.
- **7 (por componente):** corre aislado, recibe y entrega solo referencias, y su resultado coincide con la línea base.
- **8:** el flujo completo corre sin que ningún componente conozca rutas ni a otros componentes.
