import { useState, useEffect, useMemo } from 'react';
import { classifyPrompt, getModels } from '../api/client';
import CodeSnippetsModal from './CodeSnippetsModal';

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000';

const PRESETS = [
  { label: 'Code Refactor', text: 'Can you help me debug this python script that throws a RecursionError in a DFS graph traversal and refactor it with type hints?' },
  { label: 'Summary', text: 'Summarize the following quarterly earnings report into 3 crisp bullet points with key revenue and EBITDA takeaways...' },
  { label: 'Creative', text: 'Write an atmospheric sci-fi vignette about an AI model broker negotiating compute tokens in neo-Tokyo.' },
  { label: 'Chat', text: 'Hi there! Could you give me three quick tips for improving morning focus?' },
  { label: 'Architecture', text: 'Design a globally distributed event-driven payment ledger with idempotent consumers, outbox pattern, and CDC.' },
  { label: 'Formal Proof', text: 'Prove formally that the Halting Problem is undecidable using a diagonal argument and reduction to Turing machines.' },
];

const BUDGET_LEVELS = ['Free', 'Budget', 'Value', 'Pro', 'Any'];
const VOLUME_PRESETS = [
  { label: '10K', count: 10000 },
  { label: '100K', count: 100000 },
  { label: '500K', count: 500000 },
  { label: '2M', count: 2000000 },
];

export default function Playground({ modelsCount }) {
  const [input, setInput] = useState('');
  const [budget, setBudget] = useState(4); // index in BUDGET_LEVELS
  const [strategy, setStrategy] = useState('balanced'); // 'balanced' | 'cost_optimized' | 'quality_optimized'
  
  const [allModels, setAllModels] = useState([]);
  const [selectedProviders, setSelectedProviders] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [contextFilter, setContextFilter] = useState('All');
  const [showMore, setShowMore] = useState(false);
  
  const [classification, setClassification] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  
  const [showSetup, setShowSetup] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [showSnippets, setShowSnippets] = useState(false);
  const [volumeTier, setVolumeTier] = useState(1);
  const [enablePromptCache, setEnablePromptCache] = useState(false);
  const [customCompareModels, setCustomCompareModels] = useState(new Set());
  const [executions, setExecutions] = useState([]);
  const [isExecuting, setIsExecuting] = useState(false);

  const toggleCustomCompare = (modelId) => {
    setCustomCompareModels(prev => {
      const next = new Set(prev);
      if (next.has(modelId)) next.delete(modelId);
      else next.add(modelId);
      return next;
    });
  };

  useEffect(() => {
    getModels().then(data => {
      if (data) {
        setAllModels(data);
        const providers = new Set(data.map(m => m.provider || 'unknown'));
        setSelectedProviders(providers);
      }
    }).catch(console.warn);
  }, []);

  const handleExportJSON = () => {
    if (!classification) return;
    const exportData = {
      prompt: input,
      timestamp: new Date().toISOString(),
      strategy: strategy,
      classification: {
        tier: classification.tier,
        score: classification.score,
        tags: classification.tags,
        category_scores: classification.category_scores,
      },
      top_recommendation: classification.recommendations?.[0],
      all_recommendations: classification.recommendations,
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `llm_router_classification_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleAnalyze = async (textToAnalyze, strategyOverride) => {
    const text = typeof textToAnalyze === 'string' ? textToAnalyze : input;
    if (!text.trim() || isAnalyzing) return;
    setIsAnalyzing(true);
    setError(null);
    setExecutions([]);
    try {
      const activeStrategy = strategyOverride || strategy;
      const res = await fetch(API_BASE + '/v1/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Provider-Keys': localStorage.getItem('provider_keys') || '{}' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: text }],
          budget: BUDGET_LEVELS[budget],
          providers: Array.from(selectedProviders),
          strategy: activeStrategy,
        })
      });
      if (!res.ok) throw new Error('API error ' + res.status);
      const data = await res.json();
      setClassification(data);
    } catch (e) {
      console.error(e);
      setError('Analysis failed — is the backend running on ' + API_BASE + ' ?');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleExecute = async (modelIds) => {
    if (!input.trim() || isExecuting || !modelIds.length) return;
    setIsExecuting(true);
    setExecutions(modelIds.map(id => ({ model: id, loading: true, result: '', meta: null })));

    try {
      const res = await fetch(API_BASE + '/v1/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Provider-Keys': localStorage.getItem('provider_keys') || '{}' },
        body: JSON.stringify({
          models: modelIds,
          messages: [{ role: 'user', content: input }],
        })
      });
      if (!res.ok) throw new Error('API error ' + res.status);
      const data = await res.json();
      const updated = data.results.map(r => ({
        model: r.model,
        loading: false,
        result: r.error ? `Error: ${r.error}` : r.content,
        meta: {
          latency_ms: r.latency_ms,
          cost_actual_usd: r.cost_usd,
          prompt_tokens: r.prompt_tokens,
          completion_tokens: r.completion_tokens,
          provider: r.provider,
          tier: r.tier,
          is_cheapest: r.model === data.cheapest_model,
          is_fastest: r.model === data.fastest_model,
        }
      }));
      setExecutions(updated);
    } catch (e) {
      console.error(e);
      setExecutions(prev => prev.map(item => ({ ...item, loading: false, result: 'Error executing comparison.' })));
    } finally {
      setIsExecuting(false);
    }
  };

  // Debounced auto-analyze
  useEffect(() => {
    if (!input.trim()) {
      setClassification(null);
      return;
    }
    const timer = setTimeout(() => {
      handleAnalyze(input);
    }, 600);
    return () => clearTimeout(timer);
  }, [input, budget, selectedProviders, strategy]);

  // Derived providers data
  const providersMap = useMemo(() => {
    const p = {};
    allModels.forEach(m => {
      const name = m.provider || 'unknown';
      p[name] = (p[name] || 0) + 1;
    });
    return Object.entries(p).sort((a,b) => b[1] - a[1]);
  }, [allModels]);

  const toggleProvider = (p) => {
    const next = new Set(selectedProviders);
    if (next.has(p)) next.delete(p);
    else next.add(p);
    setSelectedProviders(next);
  };

  // Filter models for catalog display
  const filteredModels = useMemo(() => {
    let res = allModels.filter(m => selectedProviders.has(m.provider || 'unknown'));
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      res = res.filter(m => (m.name||'').toLowerCase().includes(q) || m.id.toLowerCase().includes(q));
    }
    const b = BUDGET_LEVELS[budget].toLowerCase();
    if (b !== 'any') {
      if (b === 'free') res = res.filter(m => (m.price_in || 0) === 0);
      else if (b === 'budget') res = res.filter(m => (m.price_in || 0) <= 0.5);
      else if (b === 'value') res = res.filter(m => (m.price_in || 0) <= 2.0);
      else if (b === 'pro') res = res.filter(m => (m.price_in || 0) > 2.0);
    }
    if (contextFilter !== 'All') {
      if (contextFilter === '128k+') res = res.filter(m => (m.context_length || 0) >= 128000);
      else if (contextFilter === '200k+') res = res.filter(m => (m.context_length || 0) >= 200000);
      else if (contextFilter === '1M+') res = res.filter(m => (m.context_length || 0) >= 1000000);
    }
    return res.sort((a, b) => a.id.localeCompare(b.id));
  }, [allModels, selectedProviders, searchQuery, budget, contextFilter]);

  const modelsToShow = showMore ? filteredModels : filteredModels.slice(0, 10);

  return (
    <div className="h-full flex flex-col lg:flex-row p-6 gap-6 overflow-hidden max-w-[1400px] mx-auto text-[#111]">
      {/* LEFT COLUMN: Prompt */}
      <div className="w-full lg:w-[32%] flex flex-col gap-5 overflow-y-auto pr-2 pb-4">
        
        {/* Presets */}
        <div className="flex flex-wrap gap-2">
          {PRESETS.map(p => (
            <button
              key={p.label}
              onClick={() => setInput(p.text)}
              className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Textarea */}
        <div className="relative flex-1 min-h-[300px]">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter your prompt to find the best model..."
            className="w-full h-full p-4 pb-12 rounded-xl border border-gray-200 bg-white resize-none outline-none focus:border-gray-400 text-[14px] shadow-sm font-sans"
          />
          <div className="absolute bottom-3 left-4 text-xs text-gray-400 font-mono flex items-center gap-2">
            <span>~{Math.ceil(input.length / 4)} tokens</span>
            <span>·</span>
            <span>{input.length} chars</span>
          </div>
          <div className="absolute bottom-3 right-4 flex gap-2">
            {input && (
              <button 
                onClick={() => setInput('')} 
                className="px-2.5 py-1 text-xs text-gray-500 hover:text-black font-medium border border-gray-200 rounded-md bg-white hover:bg-gray-50 transition-colors"
              >
                Clear
              </button>
            )}
            <button 
              onClick={() => handleAnalyze(input)} 
              disabled={isAnalyzing || !input.trim()}
              className="px-3 py-1 text-xs text-white font-medium bg-black rounded-md hover:bg-gray-800 disabled:opacity-50 transition-colors shadow-sm"
            >
              {isAnalyzing ? 'Analyzing...' : 'Analyze'}
            </button>
          </div>
        </div>

        {/* Budget */}
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col gap-4">
          <div className="flex justify-between items-center text-sm font-semibold">
            <span>Set Budget</span>
            <span className="text-gray-500 font-normal">{BUDGET_LEVELS[budget]}</span>
          </div>
          <input
            type="range"
            min="0"
            max="4"
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
            className="w-full accent-black cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-gray-400 font-medium">
            {BUDGET_LEVELS.map((lbl, idx) => (
              <span key={lbl} className={budget === idx ? "text-black" : ""}>{lbl}</span>
            ))}
          </div>
        </div>

        {/* Routing Strategy Profile */}
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col gap-3">
          <div className="flex justify-between items-center text-sm font-semibold">
            <span>Routing Strategy</span>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 font-medium capitalize">
              {strategy.replace('_', ' ')}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-1.5 p-1 bg-gray-100 rounded-lg text-xs font-medium">
            <button
              type="button"
              onClick={() => setStrategy('cost_optimized')}
              className={`py-1.5 px-2 rounded-md transition-all text-center ${
                strategy === 'cost_optimized'
                  ? 'bg-white text-black font-semibold shadow-xs'
                  : 'text-gray-500 hover:text-black'
              }`}
            >
              💰 Cost
            </button>
            <button
              type="button"
              onClick={() => setStrategy('balanced')}
              className={`py-1.5 px-2 rounded-md transition-all text-center ${
                strategy === 'balanced'
                  ? 'bg-white text-black font-semibold shadow-xs'
                  : 'text-gray-500 hover:text-black'
              }`}
            >
              ⚡ Balanced
            </button>
            <button
              type="button"
              onClick={() => setStrategy('quality_optimized')}
              className={`py-1.5 px-2 rounded-md transition-all text-center ${
                strategy === 'quality_optimized'
                  ? 'bg-white text-black font-semibold shadow-xs'
                  : 'text-gray-500 hover:text-black'
              }`}
            >
              🎯 Quality
            </button>
          </div>
          <p className="text-[11px] text-gray-500 leading-tight">
            {strategy === 'cost_optimized' && 'Favors cheap & medium models (Ceiling: 0.45, Floor: 0.75).'}
            {strategy === 'balanced' && 'Balanced trade-off between price and intelligence (0.35 / 0.65).'}
            {strategy === 'quality_optimized' && 'Prioritizes frontier reasoning and precision (0.25 / 0.50).'}
          </p>
        </div>

        {/* Analyze Button */}
        <button 
          onClick={handleAnalyze}
          disabled={isAnalyzing || !input.trim()}
          className="w-full py-3.5 bg-black text-white text-[15px] font-semibold rounded-xl hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md flex justify-center items-center gap-2"
        >
          {isAnalyzing ? 'Analyzing...' : 'Analyze →'}
        </button>
        {error && (
          <div className="mt-2 text-[13px] text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
            {error}
          </div>
        )}

        {/* Setup Collapsible */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mt-2">
          <button 
            onClick={() => setShowSetup(!showSetup)}
            className="w-full p-4 flex justify-between items-center text-sm font-semibold hover:bg-gray-50 transition-colors"
          >
            How it works & setup
            <span className="text-gray-400">{showSetup ? '−' : '+'}</span>
          </button>
          {showSetup && (
            <div className="p-4 pt-0 text-[13px] text-gray-600 space-y-3 leading-relaxed border-t border-gray-100 mt-2 pt-3">
              <p><strong>1. Type</strong> your prompt or select a preset.</p>
              <p><strong>2. Analyze:</strong> Jev classifies complexity and suggests the most cost-effective models among your selected providers.</p>
              <p><strong>3. Use:</strong> Copy the model name or use the API endpoint directly in your app.</p>
            </div>
          )}
        </div>
      </div>

      {/* CENTER COLUMN: Analysis & Recommendation */}
      <div className="w-full lg:w-[35%] flex flex-col gap-5 overflow-y-auto pr-2 pb-4">
        {classification ? (
          <>
            {/* RECOMMENDATION */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col gap-5">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold tracking-widest text-gray-400 uppercase">
                    Recommendation · {selectedProviders.size} Providers
                  </span>
                  {classification.tier && (
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      classification.tier === 'frontier' ? 'bg-purple-100 text-purple-700' :
                      classification.tier === 'medium' ? 'bg-blue-100 text-blue-700' :
                      'bg-emerald-100 text-emerald-700'
                    }`}>
                      {classification.tier}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5">
                  <button 
                    onClick={() => setShowSnippets(true)}
                    title="View API integration snippets for this model"
                    className="px-2.5 py-1 text-[11px] font-medium text-gray-600 hover:text-black border border-gray-200 rounded-md hover:bg-gray-50 flex items-center gap-1 transition-colors"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                    Connect API
                  </button>
                  <button 
                    onClick={handleExportJSON}
                    title="Export classification and recommendations as JSON"
                    className="px-2.5 py-1 text-[11px] font-medium text-gray-600 hover:text-black border border-gray-200 rounded-md hover:bg-gray-50 flex items-center gap-1 transition-colors"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                    Export JSON
                  </button>
                </div>
              </div>
              
              {/* Top Model */}
              {classification.recommendations?.length > 0 ? (
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-[22px] font-bold leading-tight">{classification.recommendations[0].model_id}</div>
                      <div className="text-[13px] text-gray-500 mt-1">{classification.recommendations[0].provider} · ${(classification.recommendations[0].price_in||0).toFixed(2)}/M in</div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <div className="text-[18px] font-semibold text-emerald-600">
                        {Math.round(classification.recommendations[0].confidence * 100)}%
                      </div>
                      <button 
                        onClick={() => navigator.clipboard.writeText(classification.recommendations[0].model_id)}
                        className="px-3 py-1.5 border border-gray-200 rounded-md text-xs font-semibold hover:bg-gray-50"
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-500">No models match criteria.</div>
              )}

              {/* List */}
              {classification.recommendations?.length > 1 && (
                <div className="flex flex-col gap-3 mt-2">
                  {classification.recommendations.slice(1, 5).map(r => (
                    <div key={r.model_id} className="flex flex-col gap-1.5">
                      <div className="flex justify-between items-center text-[13px]">
                        <span className="font-medium truncate max-w-[70%]">{r.model_id}</span>
                        <span className="text-gray-500 font-mono">{Math.round(r.confidence * 100)}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-black rounded-full" style={{ width: `${r.confidence * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* ANALYSIS */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col gap-5">
              <div className="text-[10px] font-bold tracking-widest text-gray-400 uppercase">
                Analysis
              </div>
              
              <div className="flex items-end gap-3 border-b border-gray-100 pb-4">
                <div className="text-[32px] font-bold leading-none">{classification.score?.toFixed(1) || '0.0'}</div>
                <div className="text-[14px] text-gray-500 mb-1 font-medium">/ 1.0 Complexity</div>
              </div>

              {classification.category_scores && (
                <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                  {Object.entries(classification.category_scores).map(([cat, val]) => (
                    <div key={cat} className="flex flex-col gap-1.5">
                      <div className="flex justify-between text-[12px] font-medium text-gray-600">
                        <span>{cat}</span>
                        <span>{Math.round(val * 100)}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-black rounded-full" style={{ width: `${val * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {classification.tags?.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-2">
                  {classification.tags.map(t => (
                    <span key={t} className="px-2.5 py-1 bg-gray-100 text-gray-700 text-[11px] font-semibold rounded-md">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* SAVINGS ESTIMATE */}
            {classification.recommendations?.length > 0 && (() => {
              const top = classification.recommendations[0];
              // Most expensive frontier model in the catalog as baseline
              const allRecs = classification.recommendations;
              const maxPriceIn = Math.max(...allRecs.map(r => r.price_in || 0), 10);
              const maxPriceOut = Math.max(...allRecs.map(r => r.price_out || 0), 50);
              // Estimate cost per request (avg ~500 input tokens, ~300 output tokens)
              const avgInputTokens = 500;
              const avgOutputTokens = 300;
              const hasCacheSupport = top.price_cache_read !== undefined && top.price_cache_read !== null;
              const effectiveInPrice = (enablePromptCache && hasCacheSupport)
                ? (top.price_cache_read * 0.8 + (top.price_in || 0) * 0.2)
                : (top.price_in || 0);
              const costRecommended = (effectiveInPrice * avgInputTokens / 1_000_000) + ((top.price_out || 0) * avgOutputTokens / 1_000_000);
              const costFrontier = (maxPriceIn * avgInputTokens / 1_000_000) + (maxPriceOut * avgOutputTokens / 1_000_000);
              const savedPerReq = Math.max(0, costFrontier - costRecommended);
              const savedPct = costFrontier > 0 ? (savedPerReq / costFrontier * 100) : 0;
              const savedPer1K = savedPerReq * 1000;

              return (
                <div className="bg-gradient-to-br from-emerald-50 to-white rounded-xl border border-emerald-200 p-5 shadow-sm flex flex-col gap-4">
                  <div className="flex justify-between items-center">
                    <div className="text-[10px] font-bold tracking-widest text-emerald-600 uppercase flex items-center gap-2">
                      <span>💰</span> Savings Estimate
                    </div>
                    {hasCacheSupport && (
                      <button
                        onClick={() => setEnablePromptCache(!enablePromptCache)}
                        className={`text-[10px] px-2 py-0.5 rounded font-semibold transition-all flex items-center gap-1 ${
                          enablePromptCache
                            ? 'bg-emerald-700 text-white shadow-2xs'
                            : 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200'
                        }`}
                        title="Simulate prompt prefix caching with 80% cache hit ratio"
                      >
                        ⚡ {enablePromptCache ? 'Prompt Cache: Active (80%)' : '+ Prompt Cache'}
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="flex flex-col">
                      <div className="text-[10px] text-gray-400 font-medium uppercase">
                        {enablePromptCache && hasCacheSupport ? 'Per Req (Cached)' : 'Per Request'}
                      </div>
                      <div className="text-lg font-bold text-emerald-600">${costRecommended.toFixed(5)}</div>
                      <div className="text-[10px] text-gray-400 line-through">${costFrontier.toFixed(5)}</div>
                    </div>
                    <div className="flex flex-col">
                      <div className="text-[10px] text-gray-400 font-medium uppercase">Per 1K Reqs</div>
                      <div className="text-lg font-bold text-emerald-600">${savedPer1K.toFixed(2)}</div>
                      <div className="text-[10px] text-emerald-500 font-semibold">saved</div>
                    </div>
                    <div className="flex flex-col items-end">
                      <div className="text-[10px] text-gray-400 font-medium uppercase">Reduction</div>
                      <div className={`text-lg font-bold ${savedPct > 50 ? 'text-emerald-600' : savedPct > 20 ? 'text-emerald-500' : 'text-gray-600'}`}>
                        {savedPct.toFixed(0)}%
                      </div>
                      <div className="text-[10px] text-gray-400">vs frontier</div>
                    </div>
                  </div>
                  <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-emerald-400 to-emerald-600 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, savedPct)}%` }}
                    />
                  </div>

                  {/* Volume Projection */}
                  <div className="pt-2 border-t border-emerald-100 flex flex-col gap-2">
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="text-gray-500 font-medium">Monthly volume scale:</span>
                      <div className="flex gap-1">
                        {VOLUME_PRESETS.map((vol, vIdx) => (
                          <button
                            key={vol.label}
                            onClick={() => setVolumeTier(vIdx)}
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors ${
                              volumeTier === vIdx
                                ? 'bg-emerald-600 text-white shadow-2xs'
                                : 'bg-emerald-100/60 text-emerald-800 hover:bg-emerald-200'
                            }`}
                          >
                            {vol.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="flex justify-between items-center text-xs bg-white/80 p-2 rounded-lg border border-emerald-100 font-mono">
                      <span className="text-gray-500 font-sans">Projected Net Savings:</span>
                      <span className="text-emerald-700 font-bold">
                        ${(savedPerReq * VOLUME_PRESETS[volumeTier].count).toFixed(2)}/mo
                        <span className="text-[10px] text-emerald-600 font-normal ml-1">
                          (${((savedPerReq * VOLUME_PRESETS[volumeTier].count) * 12).toFixed(0)}/yr)
                        </span>
                      </span>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* DECISION TRACE ACCORDION */}
            {classification.decision_trace && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-2">
                <button
                  onClick={() => setShowTrace(!showTrace)}
                  className="w-full p-4 flex justify-between items-center text-sm font-semibold hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span>🔬</span>
                    <span>Decision Trace & Explanations</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-700 capitalize">
                      {classification.detected_intent || classification.decision_trace.detected_intent || 'analysis'}
                    </span>
                  </div>
                  <span className="text-gray-400">{showTrace ? '−' : '+'}</span>
                </button>
                {showTrace && (
                  <div className="p-4 pt-0 border-t border-gray-100 flex flex-col gap-4 text-xs">
                    {/* Heuristic Signals */}
                    <div className="pt-3">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-2">
                        Activated Heuristic Signals
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-gray-500 font-mono text-[11px] p-2 bg-gray-50 rounded-lg">
                          <span>Base Prior Neutral Score</span>
                          <span className="font-semibold text-gray-700">0.18</span>
                        </div>
                        {(classification.decision_trace.signals || []).map((s, idx) => (
                          <div key={idx} className="flex justify-between items-center p-2 rounded-lg border border-gray-100 bg-white shadow-2xs">
                            <div className="flex flex-col">
                              <span className="font-semibold text-gray-800">{s.signal}</span>
                              <span className="text-[10px] text-gray-400">{s.detail}</span>
                            </div>
                            <span className={`font-mono font-bold text-[12px] ${s.delta >= 0 ? 'text-purple-600' : 'text-emerald-600'}`}>
                              {s.delta >= 0 ? `+${s.delta}` : s.delta}
                            </span>
                          </div>
                        ))}
                        <div className="flex justify-between items-center text-[12px] font-bold p-2.5 bg-black text-white rounded-lg">
                          <span>Final Calculated Complexity</span>
                          <span>{classification.score?.toFixed(2)} / 1.0</span>
                        </div>
                        {classification.decision_trace.strategy && (
                          <div className="flex items-center justify-between p-2 bg-gray-50 border border-gray-100 rounded-lg text-gray-700 font-mono text-[11px]">
                            <div>
                              <span className="text-gray-400">Strategy: </span>
                              <span className="font-semibold capitalize text-black">
                                {classification.decision_trace.strategy.replace('_', ' ')}
                              </span>
                            </div>
                            {classification.decision_trace.thresholds && (
                              <div className="text-[10px]">
                                <span className="text-gray-400">Ceiling: </span>
                                <span className="font-semibold text-emerald-600">{classification.decision_trace.thresholds.cheap_ceiling}</span>
                                <span className="text-gray-300 mx-1">|</span>
                                <span className="text-gray-400">Floor: </span>
                                <span className="font-semibold text-purple-600">{classification.decision_trace.thresholds.frontier_floor}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Planned Fallback Chain */}
                    {classification.decision_trace.planned_fallback_chain && (
                      <div>
                        <div className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-2">
                          Resilience Fallback Sequence
                        </div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {classification.decision_trace.planned_fallback_chain.map((mod, i) => (
                            <div key={i} className="flex items-center gap-1.5">
                              <span className={`px-2.5 py-1 rounded-md text-[11px] font-mono font-medium ${
                                i === 0 ? 'bg-black text-white shadow-xs' : 'bg-gray-100 text-gray-700'
                              }`}>
                                {i === 0 ? 'Primary: ' : `${i + 1}. `}{mod}
                              </span>
                              {i < classification.decision_trace.planned_fallback_chain.length - 1 && (
                                <span className="text-gray-400 font-bold">→</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Raw Data */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-4">
              <button 
                onClick={() => setShowRaw(!showRaw)}
                className="w-full p-4 flex justify-between items-center text-sm font-semibold hover:bg-gray-50 transition-colors"
              >
                Raw data
                <span className="text-gray-400">{showRaw ? '−' : '+'}</span>
              </button>
              {showRaw && (
                <div className="p-4 pt-0 border-t border-gray-100 bg-gray-50">
                  <pre className="text-[11px] text-gray-600 overflow-x-auto p-2 font-mono">
                    {JSON.stringify(classification, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* EXECUTION RESULT */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col gap-4">
              <div className="flex flex-wrap justify-between items-center gap-2">
                <div className="text-[10px] font-bold tracking-widest text-gray-400 uppercase">
                  Execution Compare
                </div>
                <div className="flex gap-2">
                  <button 
                    onClick={() => handleExecute([classification.recommendations[0]?.model_id])}
                    disabled={isExecuting || !classification.recommendations?.length}
                    className="px-3 py-1.5 bg-gray-100 text-gray-700 text-[11px] font-semibold rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                  >
                    Run Top
                  </button>
                  <button 
                    onClick={() => handleExecute(classification.recommendations.slice(0, 2).map(r => r.model_id))}
                    disabled={isExecuting || classification.recommendations?.length < 2}
                    className="px-3.5 py-1.5 bg-emerald-600 text-white text-[11px] font-semibold rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
                  >
                    {isExecuting ? 'Running...' : 'Compare Top 2'}
                  </button>
                  {classification.recommendations?.length >= 3 && (
                    <button 
                      onClick={() => handleExecute(classification.recommendations.slice(0, 3).map(r => r.model_id))}
                      disabled={isExecuting}
                      className="px-3 py-1.5 bg-gray-900 text-white text-[11px] font-semibold rounded-lg hover:bg-black transition-colors disabled:opacity-50 flex items-center gap-1.5"
                    >
                      Compare Top 3
                    </button>
                  )}
                  {customCompareModels.size > 0 && (
                    <button 
                      onClick={() => handleExecute(Array.from(customCompareModels))}
                      disabled={isExecuting}
                      className="px-3.5 py-1.5 bg-black text-white text-[11px] font-semibold rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
                    >
                      {isExecuting ? 'Running...' : `Compare Selected (${customCompareModels.size})`}
                    </button>
                  )}
                </div>
              </div>
              
              {executions.length > 0 && (
                <div className={`grid gap-4 ${executions.length > 2 ? 'grid-cols-1 md:grid-cols-3' : executions.length > 1 ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
                  {executions.map((exec, idx) => (
                    <div key={idx} className="flex flex-col gap-2 border border-gray-200 rounded-lg overflow-hidden bg-gray-50/50 shadow-sm">
                      <div className="px-3 py-2 bg-gray-100/80 border-b border-gray-200 text-[11px] font-semibold text-gray-700 flex justify-between items-center">
                        <div className="flex items-center gap-1.5 truncate max-w-[70%]">
                          <span className="truncate" title={exec.model}>{exec.model}</span>
                          {exec.meta?.tier && (
                            <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase ${
                              exec.meta.tier === 'frontier' ? 'bg-purple-100 text-purple-700' :
                              exec.meta.tier === 'medium' ? 'bg-blue-100 text-blue-700' :
                              'bg-emerald-100 text-emerald-700'
                            }`}>
                              {exec.meta.tier}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5">
                          {exec.loading && <span className="animate-pulse w-2 h-2 bg-blue-500 rounded-full"></span>}
                          {!exec.loading && exec.result && (
                            <button
                              onClick={() => navigator.clipboard.writeText(exec.result)}
                              title="Copy output"
                              className="text-[10px] text-gray-500 hover:text-black px-1.5 py-0.5 border border-gray-300 rounded bg-white"
                            >
                              Copy
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Badges for fastest/cheapest in comparison */}
                      {executions.length > 1 && exec.meta && (
                        <div className="px-3 pt-1 flex gap-1.5 flex-wrap">
                          {exec.meta.is_fastest && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 flex items-center gap-1">
                              ⚡ Fastest
                            </span>
                          )}
                          {exec.meta.is_cheapest && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800 flex items-center gap-1">
                              💰 Lowest Cost
                            </span>
                          )}
                        </div>
                      )}

                      <div className="p-3 text-[12px] text-gray-700 h-[220px] overflow-y-auto whitespace-pre-wrap font-sans leading-relaxed">
                        {exec.loading ? (
                          <div className="flex justify-center items-center h-full opacity-50">
                            <span className="animate-pulse">Waiting for model response...</span>
                          </div>
                        ) : exec.result}
                      </div>

                      {exec.meta && (
                        <div className="px-3 py-2 bg-white border-t border-gray-200 flex justify-between items-center text-[10px] text-gray-500 font-medium">
                          <span>{(exec.meta.latency_ms || 0).toFixed(0)}ms</span>
                          {exec.meta.prompt_tokens !== undefined && (
                            <span className="text-gray-400">{exec.meta.prompt_tokens}+{exec.meta.completion_tokens} toks</span>
                          )}
                          <span className="font-semibold text-gray-700">${(exec.meta.cost_actual_usd || 0).toFixed(5)}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
           <div className="flex-1 flex flex-col items-center justify-center text-gray-400 p-8 text-center border-2 border-dashed border-gray-200 rounded-xl">
             <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-4 text-xl">✨</div>
             <div className="font-semibold text-gray-600 mb-2">Ready to Analyze</div>
             <p className="text-[13px]">Enter a prompt on the left to see recommendations and complexity scores.</p>
           </div>
        )}
      </div>

      {/* RIGHT COLUMN: Catalog */}
      <div className="w-full lg:w-[33%] flex flex-col bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-4">
        <div className="p-5 border-b border-gray-100 flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold">Catalog</h3>
            <span className="text-[12px] font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">{filteredModels.length} models</span>
          </div>

          <div className="relative">
            <span className="absolute left-3 top-2.5 text-gray-400 text-sm">🔍</span>
            <input 
              type="text" 
              placeholder="Search..." 
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm outline-none focus:border-gray-400 transition-colors"
            />
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mr-1">Context:</span>
            {['All', '128k+', '200k+', '1M+'].map(lbl => (
              <button
                key={lbl}
                onClick={() => setContextFilter(lbl)}
                className={`px-2 py-0.5 text-[11px] font-medium rounded-md transition-colors ${
                  contextFilter === lbl 
                    ? 'bg-black text-white shadow-xs' 
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {lbl}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* Providers */}
          <div className="p-5 border-b border-gray-100">
            <div className="flex justify-between items-center mb-3">
              <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Providers</span>
              <div className="flex gap-3 text-[11px] font-semibold text-gray-500">
                <button onClick={() => setSelectedProviders(new Set())} className="hover:text-black">None</button>
                <button onClick={() => setSelectedProviders(new Set(providersMap.map(p=>p[0])))} className="hover:text-black">All</button>
              </div>
            </div>
            <div className="flex flex-col gap-2 max-h-[160px] overflow-y-auto pr-2">
              {providersMap.map(([p, count]) => (
                <label key={p} className="flex items-center justify-between cursor-pointer group">
                  <div className="flex items-center gap-2.5">
                    <input 
                      type="checkbox" 
                      checked={selectedProviders.has(p)}
                      onChange={() => toggleProvider(p)}
                      className="w-4 h-4 rounded border-gray-300 text-black focus:ring-black accent-black cursor-pointer"
                    />
                    <span className="text-[13px] font-medium text-gray-700 group-hover:text-black capitalize">{p}</span>
                  </div>
                  <span className="text-[11px] text-gray-400 font-mono">{count}</span>
                </label>
              ))}
            </div>
            <div className="text-[11px] text-gray-400 mt-4 italic">
              Jev only recommends from checked providers.
            </div>
          </div>

          {/* Model List */}
          <div className="p-5 flex flex-col gap-4">
            {modelsToShow.map(m => (
              <div key={m.id} className="flex flex-col gap-1.5 pb-3 border-b border-gray-100 last:border-0 hover:bg-gray-50/60 p-2 rounded-lg transition-colors">
                <div className="flex justify-between items-start gap-2">
                  <div className="font-semibold text-[13px] leading-tight truncate" title={m.name || m.id}>
                    {m.name || m.id}
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <button
                      onClick={() => toggleCustomCompare(m.id)}
                      title={customCompareModels.has(m.id) ? "Remove from custom comparison" : "Add to custom comparison"}
                      className={`px-1.5 py-0.5 rounded text-[9px] font-semibold transition-colors ${
                        customCompareModels.has(m.id)
                          ? 'bg-black text-white'
                          : 'bg-gray-100 text-gray-500 hover:text-black hover:bg-gray-200'
                      }`}
                    >
                      {customCompareModels.has(m.id) ? '✓ Compare' : '+ Compare'}
                    </button>
                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider ${
                      m.tier === 'frontier' ? 'bg-purple-100 text-purple-700' :
                      m.tier === 'medium' ? 'bg-blue-100 text-blue-700' :
                      'bg-emerald-100 text-emerald-700'
                    }`}>
                      {m.tier || 'cheap'}
                    </span>
                  </div>
                </div>
                <div className="text-[11px] text-gray-500 font-mono truncate" title={m.id}>{m.id}</div>
                {m.scores && (
                  <div className="flex gap-3 text-[10px] text-gray-500 font-mono">
                    <span>Reasoning: {Math.round((m.scores.Reasoning || 0) * 100)}%</span>
                    <span>Coding: {Math.round((m.scores.Coding || 0) * 100)}%</span>
                  </div>
                )}
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-gray-600 mt-0.5 font-medium">
                  <span className="flex items-center gap-1">
                    <span className="text-gray-400">Context:</span> {(m.context_length || 0).toLocaleString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="text-gray-400">In:</span> ${(m.price_in || 0).toFixed(2)}/M
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="text-gray-400">Out:</span> ${(m.price_out || 0).toFixed(2)}/M
                  </span>
                  {m.price_cache_read !== undefined && m.price_cache_read !== null && (
                    <span className="flex items-center gap-1 text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-100 font-mono text-[10px]" title="Prompt cache read price">
                      ⚡ Cache: ${(m.price_cache_read).toFixed(2)}/M
                    </span>
                  )}
                </div>
              </div>
            ))}
            
            {filteredModels.length > 10 && !showMore && (
              <button 
                onClick={() => setShowMore(true)}
                className="w-full py-2 bg-gray-50 text-[13px] font-semibold text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
              >
                More ({filteredModels.length - 10})
              </button>
            )}
          </div>
        </div>
      </div>

      {showSnippets && (
        <CodeSnippetsModal
          onClose={() => setShowSnippets(false)}
          model={classification?.recommendations?.[0]?.model_id || 'router-auto'}
          prompt={input}
        />
      )}
    </div>
  );
}
