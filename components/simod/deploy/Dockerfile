# Imagen del componente Simod (paso 7). Contexto de construcción: la raíz del repo.
# La imagen ES la herramienta: parte de nokal/simod y ejecuta `poetry run simod`
# como subproceso, sin Docker dentro de Docker (D11). No toma nada de legacy/ (D12).
FROM nokal/simod

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    ORQ_STORE_PATH=/data/store \
    ORQ_HTTP_HOST=0.0.0.0 \
    ORQ_HTTP_PORT=8000 \
    ORQ_SIMOD_HOME=/usr/src/Simod

RUN mkdir -p /data/store /app
WORKDIR /app
COPY shared/ /app/shared/
COPY components/__init__.py /app/components/__init__.py
COPY components/simod/ /app/components/simod/

EXPOSE 8000
# `python` es /opt/venv/bin/python (3.11): el mismo entorno que usa Simod, con PyYAML.
CMD ["python", "-m", "components.simod.adapter.service"]
