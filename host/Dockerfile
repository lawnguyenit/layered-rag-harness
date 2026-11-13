# Build context is the repo root (compose sets it) because the seed reads data/corpus.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /app/host
COPY host/pyproject.toml host/uv.lock host/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY host/src ./src
COPY host/migrations ./migrations
COPY host/alembic.ini ./
COPY data/corpus /app/data/corpus
RUN uv sync --frozen --no-dev
ENV PATH="/app/host/.venv/bin:$PATH" HOST_CORPUS_DIR=/app/data/corpus
RUN useradd --system --uid 10001 app && chown -R app /app
USER app
EXPOSE 8020
# Migrate, set the app role password, seed and ingest chunks (all idempotent, as the table owner); then serve as the app role.
CMD ["sh", "-c", "alembic upgrade head && python -m bepmay_host.provision && python -m bepmay_host.seed && python -m bepmay_host.ingest && exec uvicorn bepmay_host.server:app --host 0.0.0.0 --port 8020"]
