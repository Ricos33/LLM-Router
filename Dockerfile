# Multi-target Dockerfile for LLM-Router
FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create metrics storage directory
RUN mkdir -p /app/data

# Copy application source code
COPY app/ ./app/
COPY evals/ ./evals/

# ------------------------------------------------------------------------------
# Target: gateway (FastAPI reverse proxy on port 8000)
# ------------------------------------------------------------------------------
FROM base AS gateway

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ------------------------------------------------------------------------------
# Target: frontend (Vite React app on port 3000)
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend
WORKDIR /app
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build
RUN npm install -g serve
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
