FROM python:3.14.6-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

RUN python -m pip install --no-cache-dir .

RUN addgroup --system app && \
    adduser --system --ingroup app app

FROM base AS test

RUN python -m pip install --no-cache-dir ".[dev]"

COPY alembic.ini ./
COPY migrations ./migrations
COPY tests ./tests

RUN chown -R app:app /app

USER app

CMD ["python", "-m", "pytest", "-p", "no:cacheprovider"]

FROM base AS runtime

COPY alembic.ini ./
COPY migrations ./migrations

USER app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
