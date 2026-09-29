import { useState, useEffect } from 'react';
import { getModels } from '../api/client';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const BENCHMARK_PROMPTS = [
  { id: 'simple', label: 'Simple Greeting', text: 'Hello, how are you?' },
  { id: 'coding', label: 'Coding Test', text: 'Write a Python function to reverse a linked list.' },
  { id: 'reasoning', label: 'Architecture', text: 'Explain the trade-offs between monolithic and microservice architectures.' },
];

export default function Benchmark() {
  const [models, setModels] = useState([]);
  const [selectedModels, setSelectedModels] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState({}); // { [modelId]: { [promptId]: { latency, cost, text } } }
  
  useEffect(() => {
    getModels().then(data => {
      if (data) {
        setModels(data);
        // Default select one cheap, one medium, one frontier
        const cheap = data.find(m => m.tier === 'cheap');
        const med = data.find(m => m.tier === 'medium');
        const front = data.find(m => m.tier === 'frontier');
        setSelectedModels([cheap?.id, med?.id, front?.id].filter(Boolean));
      }
    });
  }, []);

  const handleToggle = (id) => {
    setSelectedModels(prev => prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]);
  };

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
          <h3 className="font-semibold text-sm mb-3">Select Models to Compare</h3>
          <div className="flex flex-col gap-2">
            {models.map(m => (
              <label key={m.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer border border-transparent hover:border-gray-100 transition-colors">
                <input 
                  type="checkbox" 
                  checked={selectedModels.includes(m.id)}
                  onChange={() => handleToggle(m.id)}
                  disabled={isRunning}
                  className="w-4 h-4 accent-black rounded border-gray-300"
                />
                <div className="flex flex-col">
                  <span className="text-[13px] font-medium leading-none">{m.name}</span>
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
                        {m?.name || id}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {BENCHMARK_PROMPTS.map(prompt => (
                  <tr key={prompt.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-4 py-4 border-r border-gray-100 align-top">
                      <div className="text-[12px] font-semibold text-gray-800 mb-1">{prompt.label}</div>
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
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
