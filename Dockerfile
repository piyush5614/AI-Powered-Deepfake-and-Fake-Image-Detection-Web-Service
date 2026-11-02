FROM node:20-alpine AS frontend-build
WORKDIR /workspace/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    MODEL_PATH=ml/artifacts/best.pt \
    MODEL_ARCH=mobilenet_v2 \
    DB_PATH=data/truthlens.db
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 truthlens \
    && mkdir -p /app/data /app/backend/static \
    && chown -R truthlens:truthlens /app
COPY backend/requirements.txt /tmp/backend-requirements.txt
COPY ml/requirements.txt /tmp/ml-requirements.txt
RUN python -m pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --no-cache-dir -r /tmp/ml-requirements.txt -r /tmp/backend-requirements.txt
COPY --chown=truthlens:truthlens backend/ ./backend/
COPY --chown=truthlens:truthlens ml/ ./ml/
COPY --from=frontend-build --chown=truthlens:truthlens /workspace/frontend/dist/ ./backend/static/
USER truthlens
EXPOSE 7860
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
