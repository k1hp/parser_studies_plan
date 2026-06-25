FROM python:3.13-slim

WORKDIR /fastapi-service

RUN pip install --no-cache-dir uv

COPY pyproject.toml .env ./

RUN uv sync

COPY ./src ./src

ENV PYTHONPATH=/fastapi-service

EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn src.entrypoint:app --host 0.0.0.0 --port 8000 --reload"]