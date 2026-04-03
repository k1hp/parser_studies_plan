FROM python:3.13-slim

WORKDIR /fastapi-service

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-cffi \
    python3-brotli \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libgobject-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY ./pyproject.toml ./

RUN uv sync

# RUN mkdir src

COPY ./src ./src

ENV PYTHONPATH=/fastapi-service

EXPOSE 8000

#CMD uv run alembic upgrade head && uv run uvicorn app.src.simple_entrypoint:app --host 0.0.0.0 --port 8000 --reload
CMD [ "sh", "-c", "uv run uvicorn src.entrypoint:app --host 0.0.0.0 --port 8000 --reload" ]