# Imagen del componente Merger (paso 7). Contexto de construcción: la raíz del repo.
# Python puro y sin dependencias: no necesita la imagen de ninguna herramienta.
# La lógica de fusión está copiada de legacy/ (ver components/merger/tool/merge_models.py);
# no se importa nada de legacy/ en tiempo de ejecución.
#
# Corre como root, igual que Simod y Prosimos (usuario de su imagen base): los tres
# comparten el volumen del almacén y las carpetas de una corrida las crea quien la
# empieza, así que un usuario sin privilegios distinto no podría escribir en ellas.
# Pendiente: definir un usuario común para todos los componentes.
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    ORQ_STORE_PATH=/data/store \
    ORQ_HTTP_HOST=0.0.0.0 \
    ORQ_HTTP_PORT=8000

RUN mkdir -p /data/store /app
WORKDIR /app
COPY shared/ /app/shared/
COPY components/__init__.py /app/components/__init__.py
COPY components/merger/ /app/components/merger/

EXPOSE 8000
CMD ["python", "-m", "components.merger.adapter.service"]
