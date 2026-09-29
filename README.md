# LLM-Router

Intelligent, OpenAI-Compatible API Gateway with Cost-Optimized Dynamic Routing. Cuts LLM inference costs by routing routine prompts to cheap/local models and reserving frontier LLMs for high-complexity reasoning.

## Quickstart

**Docker:**
```bash
cp .env.example .env
docker compose up --build
```
- Gateway: http://localhost:8000
- Dashboard: http://localhost:3000

**Local:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Dashboard: `cd web && npm install && npm run build`

## Architecture

```text
[ Client ] -> [ Gateway :8000 ] -> [ Classifier (Jev/Mock) ] 
                                  |-> Cheap Backend (Ollama/Flash)
                                  |-> Medium Backend (Agy Pro)
                                  \-> Frontier Backend (GPT-4o)
```

## Main Endpoints

- `POST /v1/chat/completions`: Standard OpenAI chat completion. Returns routing info in headers (`X-Router-Tier`, `X-Router-Model`, `X-Router-Saved-USD`).
- `POST /v1/classify`: Analyzes prompt complexity and suggests tier.

## Configuration

Set these in your `.env` file:

- `JEV_API_KEY`: TypeSafe AI key for Jev classifier
- `CLASSIFIER_MODE`: `mock` or `jev`
- `AGY_ENABLED`: `true` to use local Antigravity CLI backends
- `SIMULATE_FALLBACK`: `true` for offline testing
