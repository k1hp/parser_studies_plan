FROM python:3.13-slim

WORKDIR /fastapi-service

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    libpango1.0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml .env ./

RUN uv sync

COPY ./src ./src

ENV PYTHONPATH=/fastapi-service

EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn src.entrypoint:app --host 0.0.0.0 --port 8000 --reload"]
