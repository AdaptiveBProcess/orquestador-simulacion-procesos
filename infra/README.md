# Infraestructura

Composición de los componentes: cómo se levantan juntos y cómo se conectan en cada entorno. No contiene lógica de negocio ni de componentes.

- **Local (paso 6):** composición mínima para desarrollo, con cada componente como contenedor separado y el respaldo de datos local.
- **Otros entornos:** se agregan aquí cuando existan componentes en máquinas distintas (por ejemplo, el entrenamiento con más recursos).

Cada componente sigue construyéndose desde su propia carpeta `deploy/`.
