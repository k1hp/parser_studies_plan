FROM python:3.13-alpine

WORKDIR /fastapi-service

RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    pango-dev \
    harfbuzz-dev \
    glib-dev \
    gobject-introspection-dev \
    cairo-dev

RUN pip install --no-cache-dir uv

COPY ./pyproject.toml ./

RUN uv sync

# RUN mkdir src

COPY ./src ./src

ENV PYTHONPATH=/fastapi-service

EXPOSE 8000

#CMD uv run alembic upgrade head && uv run uvicorn app.src.simple_entrypoint:app --host 0.0.0.0 --port 8000 --reload
CMD [ "sh", "-c", "uv run uvicorn src.entrypoint:app --host 0.0.0.0 --port 8000 --reload" ]