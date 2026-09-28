<div align="center">

# ⚡ LLM-Router

**Intelligent, OpenAI-Compatible API Gateway with Cost-Optimized Dynamic Routing**

[![CI](https://github.com/Ricos33/LLM-Router/actions/workflows/ci.yml/badge.svg)](https://github.com/Ricos33/LLM-Router/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React+Vite](https://img.shields.io/badge/React+Vite-1.32+-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Tests](https://img.shields.io/badge/tests-26%2F26%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*Cut LLM inference costs by 70% to 85% by dynamically routing routine prompts to cheap/local models and reserving frontier LLMs for high-complexity reasoning.*

</div>

---

## 📌 Executive Pitch

In modern GenAI systems, **up to 80% of inbound requests** are routine queries: simple factual lookups, chit-chat greetings, formatting, basic translations, and lightweight summarizations. Paying top-tier rates ($5.00–$15.00 per 1M tokens) for frontier models like **GPT-4o** or **Claude 3.5 Sonnet** on these tasks produces massive unnecessary cloud spend.

**LLM-Router** acts as an intelligent, drop-in reverse proxy:
1. **Drop-in OpenAI Compatibility:** Point any existing `openai` client (`base_url="http://localhost:8000/v1"`) to LLM-Router without modifying application code.
2. **Intent & Complexity Classification:** Analyzes prompt complexity, code syntax, and reasoning depth in sub-millisecond time.
3. **Smart Tier Routing:** Directs simple queries to a **Cheap Backend** (e.g. local Ollama running `llama3.2:3b` at ~$0.00) and complex queries to a **Frontier Backend** (`gpt-4o`).
4. **Live Cost Telemetry:** Real-time metrics tracking requests, latency, and dollars saved via an integrated React+Vite dashboard.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    Client["Client Application\n(OpenAI SDK, LangChain, cURL)"]
    
    subgraph Gateway ["LLM-Router Gateway (:8000)"]
        API["FastAPI POST /v1/chat/completions"]
        Classifier{"Classifier Engine\n(Rule-Based Mock / Jev)"}
        Policy["Routing Policy Manager\n(Thresholds & Overrides)"]
        Metrics["SQLite Metrics Tracker\n(Latency, Tokens, Cost Saved)"]
    end
    
    subgraph Backends ["Execution Backends"]
        Cheap["Cheap / Local Backend\n(Ollama: Llama 3.2 3B)\n~$0.00 / query"]
        Frontier["Frontier Backend\n(OpenAI / OpenRouter: GPT-4o)\nHigh Reasoning"]
    end
    
    subgraph Analytics ["Telemetry (:3000)"]
        Dashboard["React+Vite Analytics Dashboard\n(Real-Time Savings & Tester)"]
    end

    Client -->|OpenAI Payload| API
    API --> Classifier
    Classifier -->|Score & Reasons| Policy
    Policy -->|Cheap Tier| Cheap
    Policy -->|Frontier Tier| Frontier
    Cheap --> API
    Frontier --> API
    API -->|Async Logging| Metrics
    Metrics -.->|Telemetry Data| Dashboard
    API -->|Response + Routing Headers| Client
```

---

## ✨ Features

- **Standard OpenAI Format:** Fully compliant `POST /v1/chat/completions` and `GET /v1/models` endpoints.
- **Typed Classifier Interface:** Clean `BaseClassifier` contract with explainable decision scoring (`score`, `confidence`, `reasons`).
- **Explainable Rule-Based Classifier:** Out-of-the-box heuristic classifier detecting code, algorithmic reasoning, formal proofs, and multi-turn complexity.
- **TypeSafe AI Jev Integration:** Native System One classifier adapter connecting to TypeSafe AI's `POST /v1/systemone` endpoint for sub-100ms intent routing and complexity scoring with calibrated probabilities and automatic fallback.
- **Configurable Routing Policy:** Override routing per-request via headers (`X-Router-Tier: cheap|frontier`) or model aliases (`router-cheap`, `router-frontier`).
- **Telemetry & Live Dashboard:** React+Vite monitoring app visualizing request volume, cheap vs. frontier breakdown, and dollar savings in real time.
- **Evaluation Benchmark Suite:** Built-in 20-prompt labeled dataset and evaluation runner with rich terminal analytics.

---

## 🚀 Quickstart

### 🐳 Lancement avec Docker

Le moyen le plus simple et rapide de lancer la stack complète (**Gateway FastAPI** et **Dashboard React+Vite**) :

1. **Configurer l'environnement :**
   ```bash
   cp .env.example .env
   ```

2. **Démarrer les services avec Docker Compose :**
   ```bash
   docker compose up --build
   ```
   *(ou en tâche de fond : `docker compose up -d --build`)*

3. **URLs des services :**
   - **Gateway FastAPI (Proxy API OpenAI-compatible) :** [`http://localhost:8000`](http://localhost:8000) (Documentation Swagger interactive sur [`http://localhost:8000/docs`](http://localhost:8000/docs))
   - **Dashboard React+Vite (Télémétrie et monitoring en temps réel) :** [`http://localhost:3000`](http://localhost:3000)

La base de données SQLite des métriques (`./data/metrics.sqlite3`) est automatiquement persistée sur l'hôte via un volume monté.

---

### 💻 Installation Locale (sans Docker)

#### 1. Prerequisites & Installation

```bash
git clone https://github.com/Ricos33/LLM-Router.git
cd LLM-Router

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment configuration:
```bash
cp .env.example .env
```
*(Optional) If you have an OpenAI API key or Ollama running locally, set them in `.env`. By default, `SIMULATE_FALLBACK=true` allows full end-to-end testing without external credentials.*

### 3. Start the Gateway

Launch the FastAPI gateway on port `8000`:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Test with `curl`:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "router-auto",
    "messages": [{"role": "user", "content": "What is the capital of France?"}]
  }'
```

Notice the diagnostic response headers:
- `X-Router-Tier: cheap`
- `X-Router-Model: llama3.2:3b`
- `X-Router-Saved-USD: 0.00115`

### 4. Launch the React+Vite Dashboard

Run the live analytics UI on port `3000`:
```bash
streamlit run dashboard/app.py
```
Open `http://localhost:3000` to view real-time traffic statistics, cumulative savings, and test prompts interactively.

### 5. Run Routing Evaluations

Benchmark classifier accuracy on the labeled dataset:
```bash
python evals/run_eval.py
```

### 6. Run Tests

```bash
pytest -v
```

---

## ⚡ Backend Agy (Local Antigravity CLI)

LLM-Router supports **AgyBackend** (`app/backends/agy.py`), enabling dynamic headless routing through your local **Google Antigravity CLI** (`agy`).

### Key Capabilities
- **Headless CLI Execution:** Executes `agy -p "<prompt>" --model <model> [--effort <effort>] --output-format text` asynchronously in a subprocess with configurable timeouts.
- **Configurable Multi-Tier Mapping:** Maps complexity tiers to models and reasoning effort:
  - **Cheap (`cheap`):** Flash model for lightweight prompts & high throughput (`gemini-3.8-flash-low`, `--effort low`).
  - **Medium (`medium`):** Pro model for balanced depth and code generation (`gemini-3.1-pro-high`, `--effort high`).
  - **Frontier (`frontier`):** Flagship model for high-complexity reasoning (`claude-opus-4-6-thinking`). Claude models omit `--effort` automatically to adhere to CLI compatibility constraints.
- **Reasoning Effort Support:** Supports CLI effort levels (`low`, `medium`, `high`, `max`) per tier where accepted by the target model.
- **Telemetry & Latency:** Accurately measures subprocess execution latency, estimates token usage, and reports upstream tier and model in response headers (`X-Router-Tier`, `X-Router-Model`, `X-Router-Latency-MS`) and React+Vite telemetry.
- **Simulation Fallback:** Seamlessly falls back to simulated responses if the binary is absent or an upstream timeout occurs when `SIMULATE_FALLBACK=true`.

### Usage Examples

```bash
# 1. Target Agy Medium tier via explicit model alias
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agy-medium",
    "messages": [{"role": "user", "content": "Explain Paxos vs Raft consensus trade-offs."}]
  }'

# 2. Target Agy Frontier tier via X-Router-Tier header (with AGY_ENABLED=true)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Router-Tier: frontier" \
  -d '{
    "model": "router-auto",
    "messages": [{"role": "user", "content": "Prove the correctness of the distributed commit protocol."}]
  }'
```

---

## 🧠 Classifieur TypeSafe AI (Jev System One)

LLM-Router s'intègre nativement avec **Jev** ([TypeSafe AI](https://typesafe.ai)), le premier modèle *System One* conçu pour la prise de décision structurée, ultra-rapide (< 100 ms) et calibrée.

### Fonctionnement & Primitives Jev
- **Endpoint Officiel :** `POST https://api.typesafe.ai/v1/systemone`
- **Authentification :** Header HTTP `Authorization: Bearer <JEV_API_KEY>`
- **Format de Requête :** Envoie l'historique des messages dans le champ `state` et évalue deux questions typées en parallèle :
  - **`tier` (`choice`) :** Sélectionne l'option optimale parmi `cheap`, `medium` et `frontier` avec une distribution de probabilités (`probabilities`) et une certitude statistique (`confidence`).
  - **`complexity` (`score`) :** Évalue la complexité cognitive et technique de la requête sur une échelle ordonnée (0 à 2, normalisé entre 0.0 et 1.0).
- **Mapping vers nos Tiers :**
  - **`cheap` :** Requêtes conversationnelles simples, salutations, faits généraux, résumés courts -> routé vers le backend Cheap (ex: Ollama Llama 3.2 3B).
  - **`medium` :** Tâches de complexité intermédiaire, explications pas-à-pas, code standard -> routé vers le backend Medium (ex: Agy Pro).
  - **`frontier` :** Raisonnement profond, architecture système distribuée, preuves mathématiques, audits de code -> routé vers le backend Frontier (ex: GPT-4o / Claude Opus).
- **Résilience & Fallback Automatique :**
  - Si `JEV_API_KEY` n'est pas configuré, un warning est loggé et le routeur bascule automatiquement sur le classifieur heuristique (`jev_mock_fallback`).
  - En cas d'erreur HTTP, rate limit ou timeout réseau, un warning est loggé et le fallback heuristique prend le relais instantanément (`jev_error_fallback`), garantissant une continuité de service totale.

### Activation

```bash
# Dans .env
CLASSIFIER_MODE=jev
JEV_API_KEY=ts_live_votre_cle_typesafe
JEV_API_BASE_URL=https://api.typesafe.ai/v1
JEV_MODEL=jev-latest
JEV_TIMEOUT=5.0
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | HTTP port for the FastAPI gateway |
| `HOST` | `0.0.0.0` | Bind host address |
| `CLASSIFIER_MODE` | `mock` | `mock` (rule-based) ou `jev` (TypeSafe AI System One) |
| `CLASSIFIER_CONFIDENCE_THRESHOLD` | `0.70` | Seuil de confiance pour les décisions de routage |
| `JEV_API_KEY` | `""` | Clé d'API TypeSafe AI (depuis https://console.typesafe.ai) |
| `JEV_API_BASE_URL` | `https://api.typesafe.ai/v1` | URL de base de l'API TypeSafe (endpoint `/v1/systemone`) |
| `JEV_MODEL` | `jev-latest` | Alias ou version du modèle Jev (`jev-latest`, `jev-1.13.0`) |
| `JEV_TIMEOUT` | `5.0` | Timeout HTTP en secondes pour l'appel de classification Jev |
| `CHEAP_PROVIDER` | `ollama` | Cheap provider (`ollama` or `openai_compatible`) |
| `CHEAP_API_BASE_URL` | `http://localhost:11434/v1` | URL for the cheap backend API |
| `CHEAP_MODEL` | `llama3.2:3b` | Target cheap model identifier |
| `CHEAP_PROMPT_PRICE_PER_M` | `0.15` | Estimated $/1M input tokens |
| `CHEAP_COMPLETION_PRICE_PER_M` | `0.60` | Estimated $/1M output tokens |
| `FRONTIER_PROVIDER` | `openai_compatible` | Frontier provider |
| `FRONTIER_API_BASE_URL` | `https://api.openai.com/v1` | URL for the frontier backend API |
| `FRONTIER_API_KEY` | `""` | Frontier API key |
| `FRONTIER_MODEL` | `gpt-4o` | Target frontier model identifier |
| `FRONTIER_PROMPT_PRICE_PER_M` | `5.00` | Estimated $/1M input tokens |
| `FRONTIER_COMPLETION_PRICE_PER_M` | `15.00` | Estimated $/1M output tokens |
| `AGY_ENABLED` | `false` | Route queries through the local Agy CLI backend |
| `AGY_BINARY_PATH` | `~/workspace/cli-tools/bin/agy` | Path to the local `agy` CLI binary |
| `AGY_TIMEOUT` | `60.0` | Subprocess execution timeout in seconds |
| `AGY_TIER_MAP` | `{"cheap": ...}` | JSON tier mapping for cheap, medium, and frontier tiers |
| `AGY_PROMPT_PRICE_PER_M` | `0.00` | Estimated $/1M input tokens for Agy CLI |
| `AGY_COMPLETION_PRICE_PER_M` | `0.00` | Estimated $/1M output tokens for Agy CLI |
| `SIMULATE_FALLBACK` | `true` | Return simulation when upstream providers are offline |
| `DATABASE_URL` | `sqlite:///./data/metrics.sqlite3` | SQLite path for metric logging |

---

## 🗺️ Roadmap

- [x] **TypeSafe AI Jev Classifier Integration:** Native System One API adapter with calibrated choice/score routing and graceful fallback.
- [ ] **SSE Streaming Support:** Low-latency streaming proxy (`stream=True`) preserving token-by-token TTFT.
- [ ] **Semantic Vector Routing:** Embedding-based similarity routing to fine-tuned domain-specific SLMs.
- [ ] **Automated Provider Fallback:** Automatic degradation/promotion on rate limits or timeout spikes (429/503).
- [ ] **Enterprise Token Budgets:** User and team-level quota enforcement.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

