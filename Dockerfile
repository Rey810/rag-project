# Single-origin deployment: FastAPI serves the API and the built React app.
# Stage 1 builds the frontend; stage 2 is the slim serving image.

FROM node:24-alpine AS client
WORKDIR /client
COPY rag-client/package.json rag-client/package-lock.json ./
RUN npm install --no-audit --no-fund
COPY rag-client/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    STATIC_DIR=/app/static \
    POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir poetry==2.3.2
COPY rag-app/pyproject.toml rag-app/poetry.lock ./
# Serving deps only; the "pipeline" group (docling, scraper deps) stays out of the image.
RUN poetry install --only main --no-root --no-interaction --no-ansi

COPY rag-app/src ./src
COPY --from=client /client/dist ./static

EXPOSE 8000
# Railway injects PORT; fall back to 8000 for local `docker run`.
CMD ["sh", "-c", "python -m uvicorn rag_app.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
