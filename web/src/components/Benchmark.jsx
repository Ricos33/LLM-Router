import { useState, useEffect, useMemo } from 'react';
import { getModels } from '../api/client';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const CATEGORY_COLORS = {
  Reasoning: 'bg-purple-100 text-purple-700',
  Coding: 'bg-blue-100 text-blue-700',
  Summary: 'bg-amber-100 text-amber-700',
  Creative: 'bg-pink-100 text-pink-700',
  Conversational: 'bg-emerald-100 text-emerald-700',
};

const DEFAULT_BENCHMARK_PROMPTS = [
  { id: 'simple', label: 'Conversational', category: 'Conversational', text: 'What is the capital of Australia and its estimated population?' },
  { id: 'coding', label: 'Coding Test', category: 'Coding', text: 'Write a Python function to reverse a singly linked list in O(n) time and O(1) space with type annotations.' },
  { id: 'reasoning', label: 'Architecture', category: 'Reasoning', text: 'Explain the trade-offs between monolithic and microservice architectures with respect to the CAP theorem.' },
  { id: 'summary', label: 'Executive Summary', category: 'Summary', text: 'Summarize the core security and performance advantages of WebAssembly versus containerization in 3 concise bullet points.' },
  { id: 'creative', label: 'Creative Scene', category: 'Creative', text: 'Write an atmospheric two-paragraph sci-fi opening about an autonomous deep-space probe waking near a rogue planet.' },
];

export default function Benchmark() {
  const [models, setModels] = useState([]);
  const [selectedModels, setSelectedModels] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [results, setResults] = useState({}); // { [modelId]: { [promptId]: { latency, cost, text } } }
  const [customPrompts, setCustomPrompts] = useState([]);
  const [showAddPrompt, setShowAddPrompt] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [newPrompt, setNewPrompt] = useState({ label: '', category: 'Reasoning', text: '' });

  const allPrompts = useMemo(() => {
    return [...DEFAULT_BENCHMARK_PROMPTS, ...customPrompts];
  }, [customPrompts]);

  const filteredPrompts = useMemo(() => {
    if (categoryFilter === 'All') return allPrompts;
    return allPrompts.filter(p => p.category === categoryFilter);
  }, [allPrompts, categoryFilter]);

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

  const handleAddPrompt = (e) => {
    e.preventDefault();
    if (!newPrompt.text.trim()) return;
    const id = `custom-${Date.now()}`;
    setCustomPrompts(prev => [...prev, {
      id,
      label: newPrompt.label.trim() || 'Custom Prompt',
      category: newPrompt.category,
      text: newPrompt.text.trim()
    }]);
    setNewPrompt({ label: '', category: 'Reasoning', text: '' });
    setShowAddPrompt(false);
  };

  const handleDeleteCustomPrompt = (id) => {
    setCustomPrompts(prev => prev.filter(p => p.id !== id));
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

  const hasCompletedResults = useMemo(() => {
    return Object.values(results).some(modelRes => 
      Object.values(modelRes || {}).some(r => r && !r.loading && !r.error)
    );
  }, [results]);

  const exportBenchmarkResults = () => {
    const exportData = {
      timestamp: new Date().toISOString(),
      models: selectedModels,
      prompts: filteredPrompts,
      summaries: modelSummaries,
      results
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `llm_router_benchmark_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportBenchmarkCSV = () => {
    const headers = ['Prompt ID', 'Category', 'Model', 'Status', 'Latency (ms)', 'Cost (USD)', 'Response Snippet'];
    const rows = [];
    for (const prompt of filteredPrompts) {
      for (const modelId of selectedModels) {
        const res = results[modelId]?.[prompt.id];
        const status = res?.error ? 'ERROR' : res?.loading ? 'RUNNING' : res?.text ? 'SUCCESS' : 'PENDING';
        const snippet = (res?.text || '').replace(/\r?\n|\r/g, ' ').slice(0, 120);
        rows.push([
          `"${prompt.id}"`,
          `"${prompt.category}"`,
          `"${modelId}"`,
          status,
          res?.latency ? Math.round(res.latency) : 0,
          res?.cost ? res.cost.toFixed(6) : 0,
          `"${snippet.replace(/"/g, '""')}"`
        ]);
      }
    }
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `llm_router_benchmark_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const runBenchmark = async () => {
    if (!selectedModels.length || isRunning) return;
    setIsRunning(true);
    setResults({});
    const totalRuns = selectedModels.length * filteredPrompts.length;
    setProgress({ current: 0, total: totalRuns });
    let completedRuns = 0;

    for (const prompt of filteredPrompts) {
      setResults(prev => {
        const next = { ...prev };
        for (const modelId of selectedModels) {
          next[modelId] = { ...(next[modelId] || {}), [prompt.id]: { loading: true } };
        }
        return next;
      });

      await Promise.all(selectedModels.map(async (modelId) => {
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
                text: data.choices[0]?.message?.content || '',
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
        } finally {
          completedRuns++;
          setProgress({ current: completedRuns, total: totalRuns });
        }
      }));
    }

    setIsRunning(false);
  };

  return (
    <div className="h-full flex flex-col p-6 overflow-hidden max-w-[1300px] mx-auto text-[#111]">
      {/* Top Header */}
      <div className="flex flex-wrap justify-between items-center gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold">Model Benchmark Suite</h2>
            <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full font-mono">
              {filteredPrompts.length} Prompts
            </span>
          </div>
          <p className="text-[13px] text-gray-500 mt-0.5">
            Execute standardized benchmark battery across models in parallel to evaluate latency, cost, and output consistency.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {hasCompletedResults && (
            <div className="flex gap-1.5">
              <button
                onClick={exportBenchmarkCSV}
                disabled={isRunning}
                className="px-3 py-2 bg-white border border-gray-200 text-gray-700 text-[12px] font-semibold rounded-lg hover:bg-gray-50 transition-colors shadow-2xs flex items-center gap-1.5"
                title="Export results as CSV"
              >
                <span>📥</span> CSV
              </button>
              <button
                onClick={exportBenchmarkResults}
                disabled={isRunning}
                className="px-3 py-2 bg-white border border-gray-200 text-gray-700 text-[12px] font-semibold rounded-lg hover:bg-gray-50 transition-colors shadow-2xs flex items-center gap-1.5"
                title="Export results as JSON"
              >
                <span>📄</span> JSON
              </button>
            </div>
          )}
          <button 
            onClick={runBenchmark}
            disabled={isRunning || !selectedModels.length}
            className="px-4 py-2 bg-black text-white text-[13px] font-semibold rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
          >
            {isRunning ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Running ({progress.current}/{progress.total})...</span>
              </>
            ) : (
              <span>Run Benchmark ({selectedModels.length * filteredPrompts.length} calls)</span>
            )}
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      {isRunning && progress.total > 0 && (
        <div className="mb-4 bg-white border border-gray-200 rounded-xl p-3 shadow-2xs flex flex-col gap-1.5">
          <div className="flex justify-between text-xs font-mono">
            <span className="text-gray-500 font-sans">Benchmarking progress:</span>
            <span className="font-semibold text-gray-800">
              {progress.current} of {progress.total} completed ({Math.round((progress.current / progress.total) * 100)}%)
            </span>
          </div>
          <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
            <div 
              className="h-full bg-black rounded-full transition-all duration-300"
              style={{ width: `${Math.round((progress.current / progress.total) * 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Category Filter and Add Custom Prompt Bar */}
      <div className="mb-4 flex flex-wrap justify-between items-center gap-2 bg-white p-2.5 rounded-xl border border-gray-200 shadow-2xs">
        <div className="flex gap-1.5 flex-wrap items-center">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mr-1">Category:</span>
          {['All', 'Reasoning', 'Coding', 'Summary', 'Creative', 'Conversational'].map(cat => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                categoryFilter === cat
                  ? 'bg-black text-white font-semibold'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <button
          onClick={() => setShowAddPrompt(!showAddPrompt)}
          className="text-xs font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 border border-gray-200 px-3 py-1 rounded-lg transition-colors flex items-center gap-1"
        >
          {showAddPrompt ? 'Cancel' : '+ Custom Prompt'}
        </button>
      </div>

      {/* Add Custom Prompt Inline Drawer */}
      {showAddPrompt && (
        <form onSubmit={handleAddPrompt} className="mb-4 bg-gray-50 border border-gray-200 rounded-xl p-4 flex flex-col gap-2.5 animate-in fade-in">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-700">Add Benchmark Prompt</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <input
              type="text"
              placeholder="Prompt Title (e.g. SQL Migration Test)"
              value={newPrompt.label}
              onChange={e => setNewPrompt({ ...newPrompt, label: e.target.value })}
              className="px-3 py-1.5 bg-white border border-gray-200 rounded text-xs outline-none"
            />
            <select
              value={newPrompt.category}
              onChange={e => setNewPrompt({ ...newPrompt, category: e.target.value })}
              className="px-3 py-1.5 bg-white border border-gray-200 rounded text-xs outline-none"
            >
              <option value="Reasoning">Reasoning</option>
              <option value="Coding">Coding</option>
              <option value="Summary">Summary</option>
              <option value="Creative">Creative</option>
              <option value="Conversational">Conversational</option>
            </select>
          </div>
          <textarea
            placeholder="Type prompt text to evaluate..."
            required
            rows={2}
            value={newPrompt.text}
            onChange={e => setNewPrompt({ ...newPrompt, text: e.target.value })}
            className="w-full p-2.5 bg-white border border-gray-200 rounded text-xs outline-none resize-none font-mono"
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowAddPrompt(false)}
              className="px-3 py-1 text-xs text-gray-500 hover:text-black"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-3.5 py-1 text-xs bg-black text-white rounded font-medium hover:bg-gray-800"
            >
              Add to Battery
            </button>
          </div>
        </form>
      )}

      {/* Main Grid: Left selector & Right table */}
      <div className="flex gap-6 h-full min-h-0">
        <div className="w-[280px] flex flex-col bg-white rounded-xl border border-gray-200 shadow-sm p-4 overflow-y-auto flex-shrink-0">
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
                {filteredPrompts.map(prompt => (
                  <tr key={prompt.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-4 py-4 border-r border-gray-100 align-top">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[12px] font-semibold text-gray-800">{prompt.label}</span>
                        {prompt.category && (
                          <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${
                            CATEGORY_COLORS[prompt.category] || 'bg-gray-100 text-gray-600'
                          }`}>
                            {prompt.category}
                          </span>
                        )}
                        {prompt.id.startsWith('custom-') && (
                          <button
                            onClick={() => handleDeleteCustomPrompt(prompt.id)}
                            className="text-gray-300 hover:text-red-600 text-xs ml-auto"
                            title="Delete custom prompt"
                          >
                            ✕
                          </button>
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
