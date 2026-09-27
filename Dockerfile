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
COPY dashboard/ ./dashboard/
COPY evals/ ./evals/

# ------------------------------------------------------------------------------
# Target: gateway (FastAPI reverse proxy on port 8000)
# ------------------------------------------------------------------------------
FROM base AS gateway

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ------------------------------------------------------------------------------
# Target: dashboard (Streamlit analytics on port 8501)
# ------------------------------------------------------------------------------
FROM base AS dashboard

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
