import { useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ABTesting() {
  const [promptA, setPromptA] = useState("You are a concise assistant. Reply in exactly one sentence.");
  const [promptB, setPromptB] = useState("You are a detailed assistant. Reply comprehensively.");
  const [userPrompt, setUserPrompt] = useState("Explain how a router works.");
  const [results, setResults] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState(null);

  const handleRun = async () => {
    setIsExecuting(true);
    setResults(null);
    setError(null);
    try {
      const res = await fetch(API_BASE + '/v1/ab-test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Provider-Keys': localStorage.getItem('provider_keys') || '{}'
        },
        body: JSON.stringify({
          system_prompt_a: promptA,
          system_prompt_b: promptB,
          user_prompt: userPrompt,
          model: "router-auto"
        })
      });
      if (!res.ok) throw new Error('API error ' + res.status);
      const data = await res.json();
      setResults(data.results);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 overflow-y-auto h-full text-txt-base">
      <h2 className="text-2xl font-bold">A/B Testing: System Prompts</h2>
      <p className="text-txt-muted text-sm">
        Compare two different system prompts side-by-side using the same routed model.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="flex flex-col gap-2">
          <label className="font-semibold text-sm">System Prompt A</label>
          <textarea 
            value={promptA}
            onChange={(e) => setPromptA(e.target.value)}
            className="w-full h-32 p-3 bg-surface border border-brd rounded-lg outline-none focus:border-gray-400 text-sm"
          />
        </div>
        <div className="flex flex-col gap-2">
          <label className="font-semibold text-sm">System Prompt B</label>
          <textarea 
            value={promptB}
            onChange={(e) => setPromptB(e.target.value)}
            className="w-full h-32 p-3 bg-surface border border-brd rounded-lg outline-none focus:border-gray-400 text-sm"
          />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <label className="font-semibold text-sm">User Prompt (Test Case)</label>
        <input 
          value={userPrompt}
          onChange={(e) => setUserPrompt(e.target.value)}
          className="w-full p-3 bg-surface border border-brd rounded-lg outline-none focus:border-gray-400 text-sm"
        />
      </div>

      <button 
        onClick={handleRun}
        disabled={isExecuting}
        className="px-6 py-3 bg-black text-white rounded-lg font-semibold hover:bg-gray-800 disabled:opacity-50"
      >
        {isExecuting ? 'Running A/B Test...' : 'Run Experiment'}
      </button>

      {error && <div className="text-red-500 bg-red-50 p-4 rounded-lg">{error}</div>}

      {results && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8 border-t border-brd pt-8">
          {results.map((r, idx) => (
            <div key={idx} className="bg-surface border border-brd rounded-lg p-5 flex flex-col gap-4 shadow-sm">
              <div className="flex justify-between items-center border-b border-brd pb-3">
                <h3 className="font-bold text-lg">Variant {r.variant}</h3>
                <span className="text-xs px-2 py-1 bg-gray-100 rounded-full font-mono text-txt-muted">{r.model_used}</span>
              </div>
              <div className="text-sm leading-relaxed whitespace-pre-wrap flex-1 min-h-[100px]">
                {r.content}
              </div>
              <div className="flex gap-4 text-xs font-mono text-txt-muted bg-base p-3 rounded mt-auto">
                <span>⏱️ {r.latency_ms.toFixed(0)}ms</span>
                <span>💰 ${(r.cost_usd || 0).toFixed(6)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
