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
RUN pip install --no-cache-dir -e ".[dev]"
COPY data/models ./data/models
EXPOSE 8742
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8742"]
