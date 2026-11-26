# Imagen de los servicios de ejemplo (paso 6.8).
# Contexto de construcción: la raíz del repo (el archivo Dockerfile.dockerignore
# de esta carpeta limita lo que se envía a `shared/`).
ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    ORQ_STORE_PATH=/data/store \
    ORQ_HTTP_HOST=0.0.0.0 \
    ORQ_HTTP_PORT=8000

# Usuario sin privilegios. La carpeta del almacén se crea con su dueño para que
# el volumen con nombre herede los permisos al montarse.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data/store \
    && chown app:app /data/store

WORKDIR /app
COPY shared/ /app/shared/

USER app
EXPOSE 8000
CMD ["python", "-m", "shared.runtime.examples.producer"]
