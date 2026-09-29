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
