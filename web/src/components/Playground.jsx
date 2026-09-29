import { useState, useEffect, useMemo } from 'react';
import { classifyPrompt, getModels } from '../api/client';

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000';

const PRESETS = [
  { label: 'Debug', text: 'Can you help me debug this python script that throws a RecursionError?' },
  { label: 'Summary', text: 'Summarize the following article in 3 bullet points...' },
  { label: 'Story', text: 'Write a creative short story about a time traveler who gets stuck in 1999.' },
  { label: 'Chat', text: 'Hi, how are you today?' },
];

const BUDGET_LEVELS = ['Free', 'Budget', 'Value', 'Pro', 'Any'];

export default function Playground({ modelsCount }) {
  const [input, setInput] = useState('');
  const [budget, setBudget] = useState(4); // index in BUDGET_LEVELS
  
  const [allModels, setAllModels] = useState([]);
  const [selectedProviders, setSelectedProviders] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [showMore, setShowMore] = useState(false);
  
  const [classification, setClassification] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  
  const [showSetup, setShowSetup] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
    getModels().then(data => {
      if (data) {
        setAllModels(data);
        const providers = new Set(data.map(m => m.provider || 'unknown'));
        setSelectedProviders(providers);
      }
    }).catch(console.warn);
  }, []);

  const handleAnalyze = async () => {
    if (!input.trim() || isAnalyzing) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      // Create request matching the new backend
      const res = await fetch(API_BASE + '/v1/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: input }],
          budget: BUDGET_LEVELS[budget],
          providers: Array.from(selectedProviders)
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
    return res.sort((a, b) => a.id.localeCompare(b.id));
  }, [allModels, selectedProviders, searchQuery, budget]);

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
          <div className="absolute bottom-3 left-4 text-xs text-gray-400 font-mono">
            {input.length} chars
          </div>
          <div className="absolute bottom-3 right-4 flex gap-2">
            <button onClick={() => setInput('')} className="px-3 py-1 text-xs text-gray-500 hover:text-black font-medium">Clear</button>
            <button className="px-3 py-1 text-xs text-gray-500 hover:text-black font-medium bg-gray-100 rounded-md">Local</button>
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
              <div className="text-[10px] font-bold tracking-widest text-gray-400 uppercase">
                Recommendation · {selectedProviders.size} Providers
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
          </>
        ) : (
           <div className="flex-1 flex flex-col items-center justify-center text-gray-400 p-8 text-center border-2 border-dashed border-gray-200 rounded-xl">
             <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-4 text-xl">✨</div>
             <div className="font-semibold text-gray-600 mb-2">Ready to Analyze</div>
             <p className="text-[13px]">Enter a prompt on the left and click Analyze to see recommendations and complexity scores.</p>
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
              <div key={m.id} className="flex flex-col gap-1.5 pb-3 border-b border-gray-50 last:border-0">
                <div className="flex justify-between items-start">
                  <div className="font-semibold text-[14px] leading-tight truncate mr-2" title={m.name || m.id}>
                    {m.name || m.id}
                  </div>
                </div>
                <div className="text-[11px] text-gray-500 truncate" title={m.id}>{m.id}</div>
                <div className="flex gap-4 text-[11px] text-gray-600 mt-1 font-medium">
                  <span className="flex items-center gap-1">
                    <span className="text-gray-400">Context:</span> {(m.context_length || 0).toLocaleString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="text-gray-400">In:</span> ${(m.price_in || 0).toFixed(2)}/M
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="text-gray-400">Out:</span> ${(m.price_out || 0).toFixed(2)}/M
                  </span>
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
    </div>
  );
}
