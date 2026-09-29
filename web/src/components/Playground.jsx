import { useState, useEffect } from 'react';
import { classifyPrompt, getModels } from '../api/client';

export default function Playground() {
  const [input, setInput] = useState('');
  const [classification, setClassification] = useState(null);
  const [allModels, setAllModels] = useState([]);
  const [selectedModelIds, setSelectedModelIds] = useState(new Set());
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    getModels().then(data => {
      if (data) {
        setAllModels(data);
        setSelectedModelIds(new Set(data.map(m => m.id)));
      }
    }).catch(console.warn);
  }, []);

  const handleAnalyze = async () => {
    if (!input.trim() || isAnalyzing) return;
    setIsAnalyzing(true);
    try {
      const res = await classifyPrompt([{ role: 'user', content: input }]);
      setClassification(res);
    } catch (e) {
      console.error(e);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const toggleModel = (id) => {
    setSelectedModelIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const confidences = classification?.probabilities || { cheap: 0, medium: 0, frontier: 0 };

  // Calculate recommended tier/model based on selected models
  let recommendedTier = classification?.tier;
  let recommendedModel = null;

  if (classification) {
    const availableTiers = new Set(
      allModels.filter(m => selectedModelIds.has(m.id) && m.tier).map(m => m.tier)
    );
    
    // Find best tier among available
    let bestTier = null;
    let maxProb = -1;
    
    for (const [tier, prob] of Object.entries(confidences)) {
      if (availableTiers.has(tier) && prob > maxProb) {
        maxProb = prob;
        bestTier = tier;
      }
    }
    
    // If no exact match or we found a best tier, fallback
    if (bestTier) {
      recommendedTier = bestTier;
      // Just pick the first selected model in this tier
      const modelsInTier = allModels.filter(m => selectedModelIds.has(m.id) && m.tier === bestTier);
      if (modelsInTier.length > 0) {
        recommendedModel = modelsInTier[0].name || modelsInTier[0].id;
      }
    } else {
        recommendedTier = "None Available";
    }
  }

  // Group models by provider
  const groupedModels = allModels.reduce((acc, m) => {
    const p = m.provider || 'unknown';
    if (!acc[p]) acc[p] = [];
    acc[p].push(m);
    return acc;
  }, {});

  return (
    <div className="h-full flex flex-col lg:flex-row p-6 gap-6 overflow-hidden max-w-[1400px] mx-auto">
      {/* LEFT: Prompt Input */}
      <div className="w-full lg:w-[40%] flex flex-col gap-4">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Write a prompt here..."
          className="flex-1 w-full p-4 rounded-xl border border-gray-200 bg-white resize-none outline-none focus:border-gray-400 text-sm shadow-sm"
        />
        <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-xs text-gray-400">{input.length} chars</span>
          <div className="flex gap-2">
            <button onClick={() => setInput('')} className="px-4 py-2 text-sm text-gray-500 hover:text-black transition-colors">
              Clear
            </button>
            <button 
              onClick={handleAnalyze}
              disabled={isAnalyzing || !input.trim()}
              className="px-4 py-2 bg-black text-white text-sm rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
            >
              {isAnalyzing ? 'Analyzing...' : 'Analyze'}
            </button>
          </div>
        </div>
      </div>

      {/* CENTER: Analysis */}
      <div className="w-full lg:w-[30%] flex flex-col bg-white rounded-xl border border-gray-200 p-6 shadow-sm overflow-y-auto">
        {!classification ? (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 text-sm text-center">
            <div className="font-semibold text-gray-500 mb-1">No analysis yet</div>
            <span className="text-xs">Type a prompt and click Analyze</span>
          </div>
        ) : (
          <div className="text-sm space-y-6">
            <div>
              <div className="text-xs text-gray-500 mb-1">Recommended Tier</div>
              <div className="font-semibold text-lg capitalize">{recommendedTier}</div>
              {recommendedModel && (
                 <div className="text-xs text-gray-400 mt-1">Model: {recommendedModel}</div>
              )}
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">Complexity Score</div>
              <div className="font-medium text-lg">{classification.score?.toFixed(2) || '—'} / 1.00</div>
            </div>
            {classification.reasons?.length > 0 && (
              <div>
                <div className="text-xs text-gray-500 mb-2">Decision Reasons</div>
                <ul className="list-disc pl-4 space-y-1.5 text-gray-700 text-xs">
                  {classification.reasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* RIGHT: Models */}
      <div className="w-full lg:w-[30%] flex flex-col bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        <div className="p-4 border-b border-gray-100 flex justify-between items-center">
          <h3 className="text-sm font-semibold">Catalog</h3>
          <span className="text-xs text-gray-400">{selectedModelIds.size} selected</span>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {Object.entries(groupedModels).map(([provider, models]) => (
            <div key={provider} className="space-y-3">
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{provider}</div>
              <div className="space-y-4">
                {models.map(m => {
                  const pct = Math.round((confidences[m.tier] || 0) * 100);
                  const isChecked = selectedModelIds.has(m.id);
                  return (
                    <div key={m.id} className={`space-y-1.5 transition-opacity ${isChecked ? 'opacity-100' : 'opacity-40'}`}>
                      <div className="flex items-center gap-2">
                        <input 
                          type="checkbox" 
                          checked={isChecked}
                          onChange={() => toggleModel(m.id)}
                          className="w-3.5 h-3.5 rounded border-gray-300 text-black focus:ring-black cursor-pointer accent-black"
                        />
                        <span className="font-medium text-sm truncate" title={m.name || m.id}>{m.name || m.id}</span>
                      </div>
                      <div className="pl-5 flex items-center gap-3">
                        <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div 
                            className="h-full rounded-full transition-all duration-300 bg-black"
                            style={{ width: `${Math.max(0, pct)}%` }} 
                          />
                        </div>
                        <span className="text-xs font-mono w-8 text-right text-gray-500">{pct}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
