import { useState, useEffect, useMemo } from 'react';
import { getModels } from '../api/client';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const BENCHMARK_PROMPTS = [
  { id: 'simple', label: 'Conversational', category: 'Reasoning', text: 'What is the capital of Australia and its estimated population?' },
  { id: 'coding', label: 'Coding Test', category: 'Coding', text: 'Write a Python function to reverse a singly linked list in O(n) time and O(1) space with type annotations.' },
  { id: 'reasoning', label: 'Architecture', category: 'Reasoning', text: 'Explain the trade-offs between monolithic and microservice architectures with respect to the CAP theorem.' },
  { id: 'summary', label: 'Executive Summary', category: 'Summary', text: 'Summarize the core security and performance advantages of WebAssembly versus containerization in 3 concise bullet points.' },
  { id: 'creative', label: 'Creative Scene', category: 'Creative', text: 'Write an atmospheric two-paragraph sci-fi opening about an autonomous deep-space probe waking near a rogue planet.' },
];

export default function Benchmark() {
  const [models, setModels] = useState([]);
  const [selectedModels, setSelectedModels] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState({}); // { [modelId]: { [promptId]: { latency, cost, text } } }
  
  const selectByTiers = (dataModels) => {
    const list = dataModels || models;
    const cheap = list.find(m => m.tier === 'cheap');
    const med = list.find(m => m.tier === 'medium');
    const front = list.find(m => m.tier === 'frontier');
    setSelectedModels([cheap?.id, med?.id, front?.id].filter(Boolean));
  };

  useEffect(() => {
    getModels().then(data => {
      if (data) {
        setModels(data);
        selectByTiers(data);
      }
    });
  }, []);

  const handleToggle = (id) => {
    setSelectedModels(prev => prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]);
  };

  const modelSummaries = useMemo(() => {
    const valid = selectedModels.map(id => {
      const modelResults = results[id] || {};
      const completed = Object.values(modelResults).filter(r => r && !r.loading && !r.error);
      const totalCost = completed.reduce((acc, curr) => acc + (curr.cost || 0), 0);
      const avgLatency = completed.length > 0 ? (completed.reduce((acc, curr) => acc + (curr.latency || 0), 0) / completed.length) : 0;
      return {
        id,
        completedCount: completed.length,
        totalCost,
        avgLatency
      };
    });

    const finished = valid.filter(v => v.completedCount > 0);
    const minCost = finished.length > 0 ? Math.min(...finished.map(f => f.totalCost)) : null;
    const minLatency = finished.length > 0 ? Math.min(...finished.map(f => f.avgLatency)) : null;

    const map = {};
    for (const v of valid) {
      map[v.id] = {
        ...v,
        isCheapest: finished.length > 1 && v.completedCount > 0 && v.totalCost === minCost,
        isFastest: finished.length > 1 && v.completedCount > 0 && v.avgLatency === minLatency,
      };
    }
    return map;
  }, [selectedModels, results]);

  const runBenchmark = async () => {
    if (!selectedModels.length || isRunning) return;
    setIsRunning(true);
    setResults({});
    
    const newResults = {};
    
    // We run the benchmark sequentially to avoid rate limits, or batch them slightly.
    for (const modelId of selectedModels) {
      newResults[modelId] = {};
      for (const prompt of BENCHMARK_PROMPTS) {
        // Init state
        setResults(prev => ({ ...prev, [modelId]: { ...prev[modelId], [prompt.id]: { loading: true } } }));
        
        try {
          const res = await fetch(`${API_BASE}/v1/chat/completions`, {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              'X-Provider-Keys': localStorage.getItem('provider_keys') || '{}'
            },
            body: JSON.stringify({
              model: modelId,
              messages: [{ role: 'user', content: prompt.text }],
              stream: false
            })
          });
          
          if (!res.ok) throw new Error('Failed');
          const data = await res.json();
          
          setResults(prev => ({
            ...prev,
            [modelId]: {
              ...prev[modelId],
              [prompt.id]: {
                loading: false,
                text: data.choices[0].message.content,
                latency: data.router_metadata?.latency_ms || 0,
                cost: data.router_metadata?.cost_actual_usd || 0
              }
            }
          }));
        } catch (e) {
          setResults(prev => ({
            ...prev,
            [modelId]: {
              ...prev[modelId],
              [prompt.id]: { loading: false, error: true }
            }
          }));
        }
      }
    }
    
    setIsRunning(false);
  };

  return (
    <div className="h-full flex flex-col p-6 overflow-hidden max-w-[1200px] mx-auto text-[#111]">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold">Model Benchmark Suite</h2>
          <p className="text-[13px] text-gray-500 mt-1">Run standard prompts against selected models to compare latency and cost.</p>
        </div>
        <button 
          onClick={runBenchmark}
          disabled={isRunning || !selectedModels.length}
          className="px-5 py-2.5 bg-black text-white text-[13px] font-semibold rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
        >
          {isRunning ? 'Benchmarking...' : 'Run Benchmark'}
        </button>
      </div>

      <div className="flex gap-6 h-full min-h-0">
        <div className="w-[300px] flex flex-col bg-white rounded-xl border border-gray-200 shadow-sm p-4 overflow-y-auto">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-sm">Select Models</h3>
            <div className="flex gap-2 text-[11px] font-semibold text-gray-500">
              <button onClick={() => selectByTiers()} disabled={isRunning} className="hover:text-black">Tiers</button>
              <span>·</span>
              <button onClick={() => setSelectedModels(models.map(m => m.id))} disabled={isRunning} className="hover:text-black">All</button>
              <span>·</span>
              <button onClick={() => setSelectedModels([])} disabled={isRunning} className="hover:text-black">None</button>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            {models.map(m => (
              <label key={m.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer border border-transparent hover:border-gray-100 transition-colors">
                <input 
                  type="checkbox" 
                  checked={selectedModels.includes(m.id)}
                  onChange={() => handleToggle(m.id)}
                  disabled={isRunning}
                  className="w-4 h-4 accent-black rounded border-gray-300 cursor-pointer"
                />
                <div className="flex flex-col truncate">
                  <span className="text-[13px] font-medium leading-none truncate" title={m.name}>{m.name}</span>
                  <span className="text-[10px] text-gray-400 mt-1 capitalize">{m.provider} · {m.tier}</span>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div className="flex-1 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col">
          <div className="overflow-x-auto overflow-y-auto h-full">
            <table className="w-full text-left border-collapse">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-[11px] font-bold text-gray-400 uppercase tracking-wider border-b border-gray-200 w-1/4">Prompt</th>
                  {selectedModels.map(id => {
                    const m = models.find(x => x.id === id);
                    return (
                      <th key={id} className="px-4 py-3 text-[11px] font-bold text-gray-600 uppercase tracking-wider border-b border-gray-200 border-l border-gray-100">
                        <div className="flex flex-col gap-0.5">
                          <span>{m?.name || id}</span>
                          <span className="text-[9px] text-gray-400 font-mono normal-case">{m?.provider || 'custom'}</span>
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {BENCHMARK_PROMPTS.map(prompt => (
                  <tr key={prompt.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-4 py-4 border-r border-gray-100 align-top">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[12px] font-semibold text-gray-800">{prompt.label}</span>
                        {prompt.category && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-gray-100 text-gray-600 uppercase">
                            {prompt.category}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-gray-500 leading-relaxed">{prompt.text}</div>
                    </td>
                    {selectedModels.map(id => {
                      const res = results[id]?.[prompt.id];
                      return (
                        <td key={id} className="px-4 py-4 border-l border-gray-100 align-top min-w-[250px]">
                          {!res ? (
                            <span className="text-[11px] text-gray-300 italic">Pending...</span>
                          ) : res.loading ? (
                            <div className="flex items-center gap-2 text-[11px] text-gray-400">
                              <div className="w-3 h-3 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
                              Running...
                            </div>
                          ) : res.error ? (
                            <span className="text-[11px] text-red-500 font-medium">Failed</span>
                          ) : (
                            <div className="flex flex-col gap-2">
                              <div className="flex gap-2 text-[10px] font-medium text-gray-500 bg-gray-50 p-1.5 rounded-md border border-gray-100">
                                <span>{(res.latency).toFixed(0)}ms</span>
                                <span>·</span>
                                <span>${(res.cost).toFixed(5)}</span>
                              </div>
                              <div className="text-[11px] text-gray-700 max-h-[120px] overflow-y-auto whitespace-pre-wrap leading-relaxed">
                                {res.text}
                              </div>
                            </div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
              {selectedModels.length > 0 && (
                <tfoot className="bg-gray-50/80 border-t-2 border-gray-200">
                  <tr>
                    <td className="px-4 py-3 font-semibold text-[12px] text-gray-700 uppercase tracking-wider">
                      Aggregate Summary
                    </td>
                    {selectedModels.map(id => {
                      const summary = modelSummaries[id];
                      if (!summary || summary.completedCount === 0) {
                        return (
                          <td key={id} className="px-4 py-3 border-l border-gray-200 text-[11px] text-gray-400 italic">
                            No runs completed
                          </td>
                        );
                      }
                      return (
                        <td key={id} className="px-4 py-3 border-l border-gray-200">
                          <div className="flex flex-col gap-1 text-[11px] font-mono">
                            <div className="flex items-center justify-between">
                              <span className="text-gray-500">Total:</span>
                              <span className="font-semibold text-gray-900">${summary.totalCost.toFixed(5)}</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-gray-500">Avg Latency:</span>
                              <span className="font-semibold text-gray-900">{Math.round(summary.avgLatency)}ms</span>
                            </div>
                            <div className="flex gap-1.5 mt-1 flex-wrap">
                              {summary.isCheapest && (
                                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800">
                                  💰 Lowest Cost
                                </span>
                              )}
                              {summary.isFastest && (
                                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-800">
                                  ⚡ Fastest
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
