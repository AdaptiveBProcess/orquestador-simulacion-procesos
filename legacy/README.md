# Repos originales

Solo `DeclarativeProcessSimulation` se agrega como submódulo; su submódulo `GenerativeLSTM` llega anidado. No se agrega `GenerativeLSTM` por separado para no duplicarlo. Esta carpeta no se modifica: los cambios se aplican como parches durante la construcción de cada componente (`docs/baseline/`).

## Agregar y fijar la versión

```
git submodule add https://github.com/DavidCepeda13/DeclarativeProcessSimulation.git legacy/DeclarativeProcessSimulation
git -C legacy/DeclarativeProcessSimulation checkout 1090059e09cfd4ff1f5d1c8e4d4e84cde45b821b
git submodule update --init --recursive
```

El último comando trae `GenerativeLSTM` en `6cc041e8b6d64bd928134ec2b36b1993ae6666d2`, que es el commit que fija el padre. Después, haz commit del puntero del submódulo en este repo.

## Cambiar de versión

Un cambio de commit en `legacy/` implica repetir la comparación contra `docs/baseline/BASELINE.md`.

## Cómo lo usan los componentes

Ninguna imagen copia `legacy/` completo. Cada `components/<x>/deploy/` declara los archivos que toma de aquí (por ejemplo, solo el jar de BIMP y no los 310 MB de `external_tools/`) y los parches que aplica. El código original asume rutas relativas al directorio de ejecución (por ejemplo `GenerativeLSTM/models_spec.ini`), así que la imagen del componente debe reproducir esa disposición.
