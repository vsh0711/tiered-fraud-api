FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY app ./app
COPY ml ./ml
COPY sim ./sim
COPY or_router ./or_router
COPY worker ./worker
COPY scripts ./scripts
COPY alembic ./alembic
COPY alembic.ini ./
COPY data/models ./data/models
RUN pip install --no-cache-dir -e .
# Bake models into the image when not already present
RUN if [ ! -f data/models/tier1.joblib ]; then PYTHONPATH=. python scripts/train_models.py; fi
RUN chmod +x scripts/entrypoint.sh
EXPOSE 8742
CMD ["./scripts/entrypoint.sh"]
