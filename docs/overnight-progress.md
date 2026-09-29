- Tue Sep 29 03:01:50 CEST 2026: Updated default mock models to realistic ones.
- Tue Sep 29 03:02:53 CEST 2026: Added real benchmark scores for accurate model recommendations in classify endpoint.
- Tue Sep 29 03:04:30 CEST 2026: Upgraded Dashboard UI to premium level with cost comparison charts and advanced metrics.
- Tue Sep 29 03:05:31 CEST 2026: Added backend fallback to frontier and classification caching for better performance.
- Tue Sep 29 03:06:18 CEST 2026: Added unit tests for classification caching, budget, and provider filtering.
- Tue Sep 29 03:06:49 CEST 2026: Added live classification with debounce in the frontend Playground.
- Tue Sep 29 03:08:15 CEST 2026: Added Recent Requests table with cost metrics to the dashboard.
- Tue Sep 29 03:10:19 CEST 2026: Added CSV export feature for request metrics in the Dashboard.
- Tue Sep 29 03:12:23 CEST 2026: Replaced cost comparison with an interactive Scatter chart plotting Cost vs Reasoning Quality in Dashboard.
- Tue Sep 29 03:13:35 CEST 2026: Enhanced Recent Requests table with actual cost and detailed classifier score.
- Tue Sep 29 03:15:09 CEST 2026: Added live Execution panel to the Playground, allowing users to send queries to the recommended model.
- Tue Sep 29 03:23:00 CEST 2026: Implemented configurable API keys per provider from the UI (Settings modal), with dynamic backend key overrides.
- Tue Sep 29 03:24:19 CEST 2026: Added Benchmark mode in a new UI tab with battery of test prompts, and comparative table of cost/latency per model.
- Tue Sep 29 03:26:13 CEST 2026: Added rate limiting via Monthly Budget tracking (backend HTTP 429) and UI progress bar alerts.
- Tue Sep 29 03:26:47 CEST 2026: Upgraded README.md to a premium portfolio version with badges, new feature highlights, and updated mermaid architecture diagram.
- Tue Sep 29 03:27:08 CEST 2026: Quota épuisé pour gemini-3.1-pro-high. Passage au modèle suivant.
- Tue Sep 29 03:37:36 CEST 2026: Updated entire model catalog to latest Sept 2026 models (23 models from 8 providers). Overhauled recommendation algorithm for proper cost-quality balancing. Tests: 44 passed, build OK.
- Tue Sep 29 03:41:15 CEST 2026: Upgraded heuristic classifier to proper three-tier routing (cheap/medium/frontier). Added creative/medium keyword detection, question complexity scoring, deep conversation depth. Tests: 44 passed.
- Tue Sep 29 03:42:29 CEST 2026: Added savings estimation panel to Playground with per-request and per-1K cost comparison. Fixed Dashboard URL concatenation bug. Build OK, 44 tests pass.
- Tue Sep 29 03:43:31 CEST 2026: Added 8 new comprehensive tests (52 total). Tests cover: all providers present, benchmark scores, pricing validity, recommendation quality by prompt type, three-tier classifier.
- Tue Sep 29 03:59:15 CEST 2026: Added /v1/analytics and /v1/catalog/summary endpoints, enhanced heuristic classifier with formal math/CS reasoning keywords, and added tier-alignment bonus to model recommendation for sharp differentiation. Tests: 54 passed, build OK.
- Tue Sep 29 04:02:10 CEST 2026: Aligned SettingsModal to 8 authorized providers, updated .env.example with placeholders, and added curated catalog documentation table to README.md. Build OK, 54 tests pass.
- Tue Sep 29 04:04:30 CEST 2026: Elevated Playground to premium tier with expanded preset prompts, direct JSON export of classification/routing metadata, and tier pill badges with benchmark scores in catalog cards. Build OK, 54 tests pass.
- Tue Sep 29 04:13:38 CEST 2026: Implemented /v1/compare endpoint with concurrent multi-model execution, centralized catalog architecture (app/catalog.py), per-model pricing in router engine, and side-by-side comparison in Playground UI with copy, latency, token count, and lowest cost/fastest badges. Fixed Benchmark API_BASE url. Tests: 56 passed, build OK.
- Tue Sep 29 04:17:00 CEST 2026: Added domain intent detection (formal_reasoning, system_architecture, code_engineering, content_summary, creative_writing) and continuous benchmark-derived category scoring in RuleBasedClassifier. Connected dynamic prompt category weights to model recommendations. Tests: 58 passed, build OK.
- Tue Sep 29 04:20:25 CEST 2026: Implemented multi-step resilient fallback chain in RouterEngine (same-tier alternative models -> frontier escalation -> simulation safety net) with X-Router-Fallback and X-Router-Fallback-Chain diagnostic headers and fallback tracking in RouterMetadata. Tests: 59 passed, build OK.





## 04:24 CEST — Épuisement total des quotas
- Les 5 modèles de la rotation sont à sec : gemini-3.1-pro-high, claude-opus-4-6-thinking, claude-sonnet-4-6, gpt-oss-120b-medium, gemini-3.8-flash-high (reset Flash estimé ~06:15 CEST).
- Tout committé et poussé sur overnight-improvements (dernier : 33cade0), main intacte.
- Fichiers QUOTA_* + QUOTA_EXHAUSTED créés. Relance automatique prévue à 06:20 CEST sur gemini-3.8-flash-high.

- Tue Sep 29 07:32:43 CEST 2026: Implemented 24h activity timeseries chart (requests/cost saved metric toggles) and top routed models performance matrix in Dashboard UI using live /v1/analytics telemetry. Tests: 59 passed, build OK.
- Tue Sep 29 07:34:54 CEST 2026: Upgraded Benchmark suite to 5 category prompts (Reasoning, Coding, Summary, Creative, Conversational), added tier quick-selectors (Tiers/All/None), and aggregate summary tfoot with lowest cost and fastest model badges. Tests: 59 passed, build OK.
- Tue Sep 29 07:37:35 CEST 2026: Implemented full Decision Trace explainability system: signal-level delta tracking in RuleBasedClassifier, /v1/classify/explain endpoint exposing weights and planned fallback sequence, and interactive Decision Trace inspector accordion in Playground UI. Tests: 61 passed, build OK.
- Tue Sep 29 07:40:11 CEST 2026: Added interactive CodeSnippetsModal in Playground UI (cURL, Python OpenAI SDK, TypeScript OpenAI SDK, REST Classify), and updated README.md portfolio documentation with architecture and quickstart SDK integration snippet. Tests: 61 passed, build OK.
- Tue Sep 29 07:43:20 CEST 2026: Implemented ProviderCircuitBreaker resilience system: consecutive failure thresholds, automatic cooldown & half-open recovery, dynamic prioritization of healthy fallback providers in RouterEngine, /v1/providers/health endpoint, and live health badges in SettingsModal. Tests: 63 passed, build OK.
- Tue Sep 29 07:46:00 CEST 2026: Enhanced Playground with interactive monthly volume savings calculator (10K to 2M scale presets with monthly/annual projections) and custom model comparison selection (+ Compare toggle on catalog cards with multi-execution runner). Tests: 63 passed, build OK.
- Tue Sep 29 07:51:30 CEST 2026: Implemented Prompt Caching Economics & Cache-Aware Savings Engine: official cached read pricing across all 23 curated models (50-90% discounts), RouterEngine cached cost and savings tracking in RouterMetadata, /v1/catalog/summary caching statistics, and interactive Playground prompt caching simulation toggle (+80% hit) and catalog card cache pricing pills. Tests: 65 passed, build OK.
- Tue Sep 29 07:56:00 CEST 2026: Upgraded Dashboard UI with Upstream Provider Circuit Health grid (8 authorized providers with live status, error counters, and auto-failover indicators), plus interactive Tier filters (All/Cheap/Medium/Frontier), prompt/model text search, and expandable request detail drawers with full prompt previews, token breakdown, and classification signals. Tests: 65 passed, build OK.
- Tue Sep 29 08:00:00 CEST 2026: Fixed and standardized SSE streaming generator in /v1/chat/completions (proper \n\n event delimiter bytes, word-level chunking, completion usage stats in final chunk, and diagnostic X-Router-* headers preservation). Tests: 65 passed, build OK.
- Tue Sep 29 08:04:00 CEST 2026: Accelerated Benchmark Suite with concurrent per-prompt model dispatch, real-time progress bar with percentage tracking, 1-click JSON benchmark results export, and distinct color-coded category badges (Reasoning, Coding, Summary, Creative, Conversational). Tests: 65 passed, build OK.
- Tue Sep 29 08:12:00 CEST 2026: Implemented Routing Strategy Profiles (balanced, cost_optimized, quality_optimized): configurable tier thresholds in RuleBasedClassifier and JevClassifier, strategy propagation in RouterEngine, X-Router-Strategy request/response headers and RouterMetadata persistence, and interactive strategy profile selector controls and threshold inspect pills in Playground UI. Tests: 68 passed, build OK.


- Tue Sep 29 06:16:58 UTC 2026: Implemented Chaos Testing API and UI controls to manually trip and restore Provider Circuit Breakers from SettingsModal and Dashboard. Tests: 71 passed, build OK.
- Tue Sep 29 06:21:13 UTC 2026: Implemented high-performance exact-match Gateway Response Cache in RouterEngine. Achieves 0ms latency and 100% cost reduction on repeated identical prompts. Added /v1/cache/clear, Settings UI integration, and live Playground cache-hit badges. Tests: 72 passed, build OK.
- Tue Sep 29 06:23:12 UTC 2026: Implemented intelligent Context Window Auto-Truncation in RouterEngine. Preserves system prompt while shedding oldest messages to strictly fit candidate model's context limits, avoiding HTTP 400 errors during deep conversations. Tests: 73 passed.
- Tue Sep 29 06:24:28 UTC 2026: Added Advanced Options Drawer to Playground UI. Users can now inject custom System Prompts and tweak Temperature/Max Tokens on the fly, which dynamically feed into the Gateway caching and routing engine. Build OK.
- Tue Sep 29 06:25:46 UTC 2026: Implemented DELETE /v1/analytics endpoint and UI 'Clear' button to wipe all telemetry and demo data cleanly on demand.
- Tue Sep 29 06:27:16 UTC 2026: Added System Prompt Quick-Select Templates to the Playground's Advanced Options drawer, giving users immediate testing personas (Coder, Writer, Data Analyst, Security).
- Tue Sep 29 06:29:36 UTC 2026: Implemented 'Per-Request Budget Enforcer'. Large prompts mapped to Frontier models are estimated for token cost; if the predicted cost exceeds the configurable 'max_cost_per_request_usd', the gateway auto-downgrades the request to MEDIUM tier to prevent bill shocks.
- Tue Sep 29 06:30:51 UTC 2026: Implemented 'API Key Pool Rotation'. Added 'frontier_api_keys_pool' config. The Gateway now load-balances requests across multiple keys to bypass provider rate limits during traffic spikes.
- Tue Sep 29 06:32:14 UTC 2026: Built a beautiful new 'Model Catalog' tab in the frontend. Users can now explore, search, and filter the entire model registry by tier and provider, complete with input/output pricing and context window metrics.
- Tue Sep 29 07:31:00 UTC 2026: Implemented JSON Mode (response_format) toggle in Playground Advanced Settings and wired it to Router Engine payload generation for OpenAI-compatible backends. Tests passed, build OK.
- Tue Sep 29 07:31:30 UTC 2026: Quota épuisé pour gemini-3.1-pro-high. Passage au modèle suivant.
- Tue Sep 29 08:04:24 UTC 2026: Enhanced heuristic classifier with multi-language keyword support (French, Spanish, German, Portuguese), math/LaTeX notation detection, and structured output keywords (JSON schema, OpenAPI, YAML). 4 new tests added. Tests: 78 passed, build OK.
- Tue Sep 29 08:08:11 UTC 2026: Implemented token estimation engine (app/tokenizer.py) and /v1/estimate-cost pre-execution cost preview API with savings summary, cache projections, and context-fit checks. Added frontend API client helpers. Tests: 91 passed, build OK.
- Tue Sep 29 08:09:47 UTC 2026: Upgraded frontend with responsive mobile layout (hamburger menu), full ARIA accessibility (tablist/tab/tabpanel, aria-selected, aria-expanded), keyboard navigation (arrows, Home, End, Escape), focus-visible indicators, reduced-motion support, and high-contrast mode compatibility. Tests: 91 passed, build OK.
- Tue Sep 29 08:14:00 UTC 2026: Quota épuisé pour claude-opus-4-6-thinking (RESOURCE_EXHAUSTED, reset ~4h47). Passage au modèle suivant.
- Tue Sep 29 08:28:00 UTC 2026: Quota épuisé pour claude-sonnet-4-6 (RESOURCE_EXHAUSTED au démarrage, reset ~4h43). Passage au modèle suivant.
- Tue Sep 29 08:31:43 UTC 2026: Upgraded Model Catalog with benchmark scores visualization (Reasoning, Coding, Summary, Creative), prompt caching discount pills, search bar, multi-criteria sorting (benchmarks, cost, context, name), and direct Route Prompt action. Tests: 91 passed, build OK.
- Tue Sep 29 08:33:34 UTC 2026: Integrated live Token & Cost Estimation Engine into Playground UI: live token counter, interactive output token selector (150/500/1000/2000), cache hit ratio slider (0-100%), and cost breakdown table comparing cheapest vs recommended vs frontier models. Tests: 91 passed, build OK.
- Tue Sep 29 08:37:58 UTC 2026: Implemented Enterprise Routing Rules & Policy Overrides Engine (app/router/rules.py). Supports regex pattern and word-boundary keyword matching, target models/tiers/providers, priority scoring, and match counting. Integrated into RouterEngine.decide_route, X-Router-Rule response headers, decision trace, and added /v1/rules REST CRUD API. 7 new tests added. Tests: 98 passed, build OK.
- Tue Sep 29 08:39:13 UTC 2026: Added Routing Rules & Policies management tab in SettingsModal. Users can inspect all active deterministic rules with match counts and priority badges, create custom keyword/tier rules via inline modal drawer, delete rules, and reset to defaults. Tests: 98 passed, build OK.
- Tue Sep 29 08:40:55 UTC 2026: Added synthetic provider health and latency probing (/v1/providers/probe) and dynamic latency sample recording in ProviderCircuitBreaker. Tracks rolling latency, average response time, and availability rate. 2 new unit tests added (100 total tests passing). Tests: 100 passed, build OK.
- Tue Sep 29 08:43:32 UTC 2026: Added 1-click query replay action from Dashboard recent requests table into Playground (auto-focusing and populating prompt), and added CSV/JSON comparison export buttons to Playground multi-model execution runner. Tests: 100 passed, build OK.
- Tue Sep 29 08:44:46 UTC 2026: Updated README.md portfolio documentation with 100 passing tests badge, updated Mermaid architecture diagram (Tokenizer, Rules Manager, Circuit Breaker), prompt caching specifications table, and 1-minute SDK quickstart. Tests: 100 passed, build OK.
- Tue Sep 29 08:45:51 UTC 2026: Added 4 new API integration tests covering X-Router-Rule response headers, decision trace rule tracking, catalog price/context invariants, and filtered pre-execution cost estimation. Total test count reached 104 passed. Tests: 104 passed, build OK.
- Tue Sep 29 08:48:10 UTC 2026: Enhanced Benchmark runner UI with CSV export support, custom prompt creator drawer with category assignments, and category filter pills (Reasoning, Coding, Summary, Creative, Conversational). Tests: 104 passed, build OK.
- Tue Sep 29 08:53:00 UTC 2026: Implemented Enterprise Budget & Threshold Alerting Engine (app/router/budget.py) with multi-stage threshold monitoring (50%, 80%, 90%, 100%), automated webhook dispatching, alert event history, and dynamic runtime configuration (/v1/budget/status, /v1/budget/configure, /v1/budget/test-alert, /v1/budget/clear-alerts). Integrated into Dashboard UI with interactive status badge, threshold progress indicators, synthetic alert testing, and inline configuration drawer. 5 new unit and API integration tests added (109 total tests passing). Tests: 109 passed, build OK.
- Tue Sep 29 08:55:00 UTC 2026: Enhanced Dashboard with Live Synthetic Provider Probing & Health Radar: added 'Probe All' trigger button calling /v1/providers/probe, real-time round-trip latency display (ms), and dynamic availability percentage metrics per provider card. Tests: 109 passed, build OK.
- Tue Sep 29 08:57:30 UTC 2026: Implemented Upstream Provider Traffic Distribution and Prompt Caching Economics Engine in MetricsTracker (app/storage/metrics.py) and Dashboard UI: calculates provider request/cost shares, total prompt tokens, and projected cache savings ($) with provider-specific discount benchmarks (up to 90%). Tests: 109 passed, build OK.
- Tue Sep 29 08:59:45 UTC 2026: Updated portfolio documentation and architecture specifications in README.md and .env.example: 109 passing tests badge, updated Mermaid architecture diagram with Budget & Alert Manager, configuration table entries for automated webhook alerting, and prompt caching economics summary. Tests: 109 passed, build OK.
- Tue Sep 29 09:01:30 UTC 2026: Expanded integration test suite with 3 comprehensive tests covering budget lifecycle (/v1/budget/*), analytics extensions (provider_stats & prompt_cache_analytics), and synthetic latency probing (/v1/providers/probe). Total passing test count reached 112 tests. Tests: 112 passed, build OK.
- Tue Sep 29 09:04:00 UTC 2026: Added 'Budget & Webhooks' management tab to SettingsModal.jsx: enables operators to configure monthly budget ceilings, notification webhook URLs, and alert threshold percentages, with real-time budget utilization status badges, synthetic test alert triggers, and alert event history management. Tests: 112 passed, build OK.
- Tue Sep 29 09:15:00 UTC 2026: Jev payload now tailored per candidate model: engine shortlists up to 6 catalog models (2/tier) and JevClassifier sends per-model fit questions (pricing, context window, benchmarks) with fit scores parsed into metadata['model_fit']/best_fit_model. 4 new tests. Tests: 116 passed.
## 29/09 14:22 - Fix Routing Strategy
- Applied routing strategy parameter (cost_optimized, quality_optimized, balanced) to the confidence scoring formula in `app/main.py`. 
- Tested via python script: different strategies route identical prompts to different models and tiers correctly.
- Tests (116) pass. Web build pass. Push successful.
## 29/09 14:24 - Jev JSON payload fine-tuning
- Updated `app/router/engine.py` to inject benchmark scores directly into the Jev candidates payload.
- Added candidate fit-scoring evaluation to `RuleBasedClassifier` (mock) so it realistically simulates Jev's tailored scoring. 
- The recommendation engine now clearly differentiates the models per category. 
- Tests (116) pass. Web build pass. Push successful.
## 29/09 14:31 - UI Premium Upgrades & Resilience Analytics
- Added debounced live-typing classification to the Playground for a premium 'instant-analyze' feel.
- Modified `ModelCompareResult` and `app/main.py` to return `fallback_triggered` metadata to the frontend.
- Added visual fallback indicator badges to the Playground to prove resilience transparency.
- Tracked `fallback_triggered` in SQLite `RequestMetric` and added Resilience Stats to the Analytics dashboard UI.
- All tests (116) pass. Web build pass. Pushed.
## 29/09 12:56 - Real Fallback with Exponential Backoff
- Implemented exponential backoff with jitter in engine.py for resilient fallback.
- Updated openai_backend.py to actually raise errors when explicit keys are passed.
- Added test_fallback.py which passes. Curl confirmed fallback from gpt-4o to claude-sonnet-5. All tests (117) pass, web build ok.
## 29/09 13:10 - Configurable Timeouts per Tier & Premium UI
- (Backend) Added `cheap_timeout_seconds`, `medium_timeout_seconds`, and `frontier_timeout_seconds` in config.py, propagated down to async HTTP clients.
- (Frontend) Built Premium Design System using Tailwind 4 CSS variables for dark/light mode (`--color-base`, `--color-surface`, `--color-txt-base`, etc.) and added Inter typography.
- (Frontend) Updated Playground to have a single "Send" button that streams responses using the router directly, fully replacing the old manual Compare workflow.
## 29/09 13:20 - Semantic Response Cache (Backlog Item 3)
- Upgraded ResponseCache from exact-match-only to semantic near-match support.
- Aggressive text normalization: strips articles, filler words, punctuation, accents; collapses whitespace.
- SequenceMatcher-based similarity (threshold 0.92) for fuzzy matching.
- Respects non-prompt params (model, temperature, strategy) in semantic matches.
- Added /v1/cache/stats endpoint exposing hit/miss/semantic_hit counts and cumulative savings.
- Curl verified: exact match HIT, semantic near-match HIT ("Please explain the Docker containers" → "Explain Docker containers"), different temperature MISS.
- 5 new tests (normalizer, similarity, exact match, semantic match, stats endpoint). Tests: 123 passed, build OK.
## 29/09 13:23 - Virtual API Keys (Backlog Item 4)
- Implemented VirtualKeyManager (app/router/virtual_keys.py) with SQLite persistence.
- Keys issued as sk-router-... with per-key budget ($), rate limit (RPM), and metadata.
- CRUD: POST/GET /v1/keys, POST /v1/keys/{id}/revoke, DELETE /v1/keys/{id}.
- Validation: POST /v1/keys/validate with Authorization: Bearer sk-router-...
- Sliding-window rate limiter (in-memory) + budget enforcement.
- 9 new tests: CRUD, revocation, deletion, budget exhaustion, rate limiting.
- Tests: 132 passed, build OK.
## 29/09 13:25 - PII Guardrails (Backlog Item 5)
- Implemented PII guardrail engine (app/router/guardrails.py).
- Detects and masks: emails, phones, IBANs, credit cards (Luhn), IPv4, SSNs.
- Support for custom regex patterns.
- Integrated with /v1/chat/completions: opt-in via PII_GUARDRAILS_ENABLED.
- API: POST /v1/guardrails/scan, GET /v1/guardrails/stats, POST /v1/guardrails/toggle.
- Logs type of PII detected, never the actual value.
- 10 new tests. Tests: 142 passed, build OK.
## 29/09 13:27 - Feedback Loop (Backlog Item 6)
- Implemented FeedbackManager (app/router/feedback.py) with SQLite persistence.
- POST /v1/feedback: submit 👍/👎 with model_id, category, session_id.
- GET /v1/feedback/stats: total votes, satisfaction rate, per-model breakdown.
- GET /v1/feedback/recent: recent feedback entries.
- GET /v1/feedback/adjustments: current score adjustments per model per category.
- Exponential-weighted adjustments (min 5 votes to activate).
- Anti-abuse: 10 votes/min per session, duplicate vote updates.
- 8 new tests. Tests: 150 passed, build OK.
## 29/09 15:44 - Fine-tuning Jev Payload & Strategy Repair
- Refined `app/classifier/jev.py` payload schema: enhanced instructions/criteria for `tier` and `complexity`, and added a new `domain` question. Improved `fit_question` instructions and criteria for candidates.
- Fixed `app/router/engine.py` routing strategy: `_build_classification_candidates` now correctly sorts models based on the selected `strategy` (cost_optimized, quality_optimized), and `decide_route` now correctly extracts `best_fit_model` from the classification metadata instead of always defaulting to the tier's default model.
- Added `tests/test_router_strategies.py` and curl tests confirming the routing strategy properly changes model selection dynamically.
- Tests (151) pass. Web build pass. Push successful.
## 29/09 15:49 - UI polish for Backlog features
- Created dedicated UIs for Virtual API Keys (creation, budget setup, RPM limits, revocation, deletion) in SettingsModal.
- Created dedicated UI for PII Guardrails (toggle enable/disable, all-time masking statistics grouped by PII type) in SettingsModal.
- Connected to `/v1/keys` and `/v1/guardrails` endpoints.
- Frontend build OK.
## 29/09 15:56 - Feedback Loop UI
- Added `response_id` extraction in backend (`ModelCompareResult`) for executed prompts.
- Built interactive 👍/👎 Feedback buttons in Playground execution panel connected to `/v1/feedback`.
- Feedback logic tracks per-execution state avoiding duplicates.
- All tests pass (152). Frontend build OK.
## 29/09 16:01 - Semantic Cache UI
- Added Semantic Cache stats dashboard card visualizing hit rate, hits vs semantic hits, and cumulative USD savings.
- Wired frontend `Dashboard.jsx` to fetch data from `/v1/cache/stats`.
- Tested build. Build OK. Pushed.
