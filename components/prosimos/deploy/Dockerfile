# Imagen del componente Prosimos (paso 7). Contexto de construcción: la raíz del repo.
# Misma base que Simod (nokal/simod, que trae Prosimos). Ejecuta `poetry run prosimos`
# como subproceso, sin Docker dentro de Docker (D11). No toma nada de legacy/ (D12).
FROM nokal/simod

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    ORQ_STORE_PATH=/data/store \
    ORQ_HTTP_HOST=0.0.0.0 \
    ORQ_HTTP_PORT=8000 \
    ORQ_PROSIMOS_HOME=/usr/src/Simod

RUN mkdir -p /data/store /app
WORKDIR /app
COPY shared/ /app/shared/
COPY components/__init__.py /app/components/__init__.py
COPY components/prosimos/ /app/components/prosimos/

EXPOSE 8000
CMD ["python", "-m", "components.prosimos.adapter.service"]
