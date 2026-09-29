#!/bin/bash
set -e
echo "Starting backend..."
.venv/bin/uvicorn app.main:app --port 8000 &
PID=$!
sleep 2
echo "Testing curl..."
curl -s http://localhost:8000/health > /dev/null
curl -s http://localhost:8000/v1/models > /dev/null
curl -s -X POST http://localhost:8000/v1/classify -H "Content-Type: application/json" -d '{"messages": [{"role": "user", "content": "hello"}]}' > /dev/null
curl -s http://localhost:8000/v1/metrics/export/csv > /dev/null
echo "Killing backend..."
kill $PID
echo "Running pytest..."
.venv/bin/pytest -q
echo "Building frontend..."
cd web && npm run build
echo "All good!"
