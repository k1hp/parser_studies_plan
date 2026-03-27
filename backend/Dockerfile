FROM python:3.13-slim

WORKDIR /fastapi-service

RUN pip install --no-cache-dir uv

COPY ./pyproject.toml ./uv.lock ./

RUN uv sync

# RUN mkdir src

COPY ./src ./src

ENV PYTHONPATH=/fastapi-service

EXPOSE 8001

#CMD uv run alembic upgrade head && uv run uvicorn app.src.simple_entrypoint:app --host 0.0.0.0 --port 8000 --reload
CMD [ "sh", "-c", "uv run uvicorn src.entrypoint:app --host 0.0.0.0 --port 8001 --reload" ]