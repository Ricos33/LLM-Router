import React, { useEffect, useState } from 'react';
import { getModels } from '../api/client';

export default function Catalog() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterProvider, setFilterProvider] = useState('All');
  const [filterTier, setFilterTier] = useState('All');

  useEffect(() => {
    getModels()
      .then(data => {
        setModels(data || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const providers = ['All', ...new Set(models.map(m => m.provider).filter(Boolean))];
  const tiers = ['All', 'frontier', 'medium', 'cheap'];

  const filtered = models.filter(m => {
    if (filterProvider !== 'All' && m.provider !== filterProvider) return false;
    if (filterTier !== 'All' && m.tier !== filterTier) return false;
    return true;
  });

  return (
    <div className="h-full flex flex-col p-8 overflow-y-auto max-w-[1400px] mx-auto text-[#111]">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Model Catalog</h1>
          <p className="text-gray-500 text-sm mt-1">Explore all {models.length} integrated LLMs across different tiers and providers.</p>
        </div>
        <div className="flex gap-4">
          <select 
            className="px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-[13px] font-medium outline-none"
            value={filterProvider}
            onChange={e => setFilterProvider(e.target.value)}
          >
            {providers.map(p => <option key={p} value={p}>{p === 'All' ? 'All Providers' : p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
          </select>
          <select 
            className="px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-[13px] font-medium outline-none"
            value={filterTier}
            onChange={e => setFilterTier(e.target.value)}
          >
            {tiers.map(t => <option key={t} value={t}>{t === 'All' ? 'All Tiers' : t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex justify-center items-center opacity-50"><span className="animate-pulse">Loading models...</span></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {filtered.map(m => (
            <div key={m.id} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-3">
                <h3 className="font-semibold text-[15px]">{m.name}</h3>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                  m.tier === 'frontier' ? 'bg-purple-100 text-purple-700' :
                  m.tier === 'medium' ? 'bg-blue-100 text-blue-700' : 'bg-emerald-100 text-emerald-700'
                }`}>
                  {m.tier}
                </span>
              </div>
              <div className="text-[12px] text-gray-500 mb-4 truncate" title={m.id}>{m.id}</div>
              
              <div className="grid grid-cols-2 gap-3 text-[12px]">
                <div className="bg-gray-50 rounded-lg p-2.5">
                  <div className="text-gray-400 font-semibold mb-0.5 uppercase tracking-wider text-[9px]">Input</div>
                  <div className="font-medium">${m.price_in.toFixed(2)} / 1M</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-2.5">
                  <div className="text-gray-400 font-semibold mb-0.5 uppercase tracking-wider text-[9px]">Output</div>
                  <div className="font-medium">${m.price_out.toFixed(2)} / 1M</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-2.5">
                  <div className="text-gray-400 font-semibold mb-0.5 uppercase tracking-wider text-[9px]">Context</div>
                  <div className="font-medium">{(m.context_length / 1000).toFixed(0)}k tokens</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-2.5">
                  <div className="text-gray-400 font-semibold mb-0.5 uppercase tracking-wider text-[9px]">Provider</div>
                  <div className="font-medium capitalize">{m.provider}</div>
                </div>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full py-20 text-center text-gray-400">
              No models match your filters.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
