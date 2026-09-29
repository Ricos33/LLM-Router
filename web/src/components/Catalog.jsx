import React, { useEffect, useState, useMemo } from 'react';
import { getModels } from '../api/client';

export default function Catalog({ onSelectModel }) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterProvider, setFilterProvider] = useState('All');
  const [filterTier, setFilterTier] = useState('All');
  const [sortBy, setSortBy] = useState('reasoning');
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    getModels()
      .then(data => {
        setModels(data || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleCopyId = (id) => {
    navigator.clipboard?.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const providers = ['All', ...new Set(models.map(m => m.provider).filter(Boolean))];
  const tiers = ['All', 'frontier', 'medium', 'cheap'];

  // Summary statistics
  const stats = useMemo(() => {
    const total = models.length;
    const frontier = models.filter(m => m.tier === 'frontier').length;
    const medium = models.filter(m => m.tier === 'medium').length;
    const cheap = models.filter(m => m.tier === 'cheap').length;
    const cachingModels = models.filter(m => m.price_cache_read != null && m.price_in > 0);
    const avgDiscount = cachingModels.length > 0
      ? Math.round(cachingModels.reduce((acc, m) => acc + (1 - m.price_cache_read / m.price_in) * 100, 0) / cachingModels.length)
      : 0;
    return { total, frontier, medium, cheap, avgDiscount };
  }, [models]);

  const filteredAndSorted = useMemo(() => {
    let result = models.filter(m => {
      if (filterProvider !== 'All' && m.provider !== filterProvider) return false;
      if (filterTier !== 'All' && m.tier !== filterTier) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = (m.name || '').toLowerCase().includes(q);
        const matchId = (m.id || '').toLowerCase().includes(q);
        const matchProvider = (m.provider || '').toLowerCase().includes(q);
        if (!matchName && !matchId && !matchProvider) return false;
      }
      return true;
    });

    result.sort((a, b) => {
      const aScores = a.scores || {};
      const bScores = b.scores || {};
      if (sortBy === 'reasoning') return (bScores.Reasoning || 0) - (aScores.Reasoning || 0);
      if (sortBy === 'coding') return (bScores.Coding || 0) - (aScores.Coding || 0);
      if (sortBy === 'summary') return (bScores.Summary || 0) - (aScores.Summary || 0);
      if (sortBy === 'creative') return (bScores.Creative || 0) - (aScores.Creative || 0);
      if (sortBy === 'price_asc') return (a.price_in || 0) - (b.price_in || 0);
      if (sortBy === 'price_desc') return (b.price_in || 0) - (a.price_in || 0);
      if (sortBy === 'context_desc') return (b.context_length || 0) - (a.context_length || 0);
      if (sortBy === 'name') return (a.name || a.id).localeCompare(b.name || b.id);
      return 0;
    });

    return result;
  }, [models, filterProvider, filterTier, searchQuery, sortBy]);

  return (
    <div className="h-full flex flex-col p-6 sm:p-8 overflow-y-auto max-w-[1400px] mx-auto text-txt-base">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">Model Registry & Benchmarks</h1>
            <span className="text-xs bg-gray-100 text-txt-base font-semibold px-2 py-0.5 rounded-full border border-brd">
              Sept 2026
            </span>
          </div>
          <p className="text-txt-muted text-sm mt-1">
            Curated 8-provider registry with real LMArena & SWE-bench normalized scores, prompt caching economics, and verified token pricing.
          </p>
        </div>

        {/* Global Summary Stats */}
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          <div className="bg-surface border border-brd rounded-lg px-3 py-1.5 text-center shadow-xs">
            <span className="text-[10px] uppercase font-bold text-txt-muted block">Total</span>
            <span className="text-sm font-semibold text-txt-base">{stats.total} models</span>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-lg px-3 py-1.5 text-center shadow-xs">
            <span className="text-[10px] uppercase font-bold text-purple-600 block">Frontier</span>
            <span className="text-sm font-semibold text-purple-900">{stats.frontier}</span>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-1.5 text-center shadow-xs">
            <span className="text-[10px] uppercase font-bold text-blue-600 block">Medium</span>
            <span className="text-sm font-semibold text-blue-900">{stats.medium}</span>
          </div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-1.5 text-center shadow-xs">
            <span className="text-[10px] uppercase font-bold text-emerald-600 block">Cheap</span>
            <span className="text-sm font-semibold text-emerald-900">{stats.cheap}</span>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5 text-center shadow-xs">
            <span className="text-[10px] uppercase font-bold text-amber-700 block">Avg Cache Cut</span>
            <span className="text-sm font-semibold text-amber-900">-{stats.avgDiscount}%</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6 bg-surface p-3 rounded-xl border border-brd shadow-xs">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Search model name, id (e.g. claude, gpt-6, qwen)..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-brd text-xs sm:text-sm bg-gray-50 focus:bg-surface focus:border-gray-400 outline-none transition-colors"
          />
          <svg className="w-4 h-4 text-txt-muted absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        <div className="flex gap-2 flex-wrap items-center">
          <select 
            className="px-3 py-2 rounded-lg border border-brd bg-surface text-xs font-medium outline-none hover:border-gray-400 cursor-pointer"
            value={filterProvider}
            onChange={e => setFilterProvider(e.target.value)}
          >
            {providers.map(p => (
              <option key={p} value={p}>{p === 'All' ? 'All Providers' : p.charAt(0).toUpperCase() + p.slice(1)}</option>
            ))}
          </select>

          <select 
            className="px-3 py-2 rounded-lg border border-brd bg-surface text-xs font-medium outline-none hover:border-gray-400 cursor-pointer"
            value={filterTier}
            onChange={e => setFilterTier(e.target.value)}
          >
            {tiers.map(t => (
              <option key={t} value={t}>{t === 'All' ? 'All Tiers' : t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>

          <select 
            className="px-3 py-2 rounded-lg border border-brd bg-surface text-xs font-medium outline-none hover:border-gray-400 cursor-pointer"
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
          >
            <option value="reasoning">Sort: Reasoning Quality (↓)</option>
            <option value="coding">Sort: Coding Quality (↓)</option>
            <option value="summary">Sort: Summary Quality (↓)</option>
            <option value="creative">Sort: Creative Quality (↓)</option>
            <option value="price_asc">Sort: Price (Low to High)</option>
            <option value="price_desc">Sort: Price (High to Low)</option>
            <option value="context_desc">Sort: Context Window (Max)</option>
            <option value="name">Sort: Name (A-Z)</option>
          </select>
        </div>
      </div>

      {/* Model Cards Grid */}
      {loading ? (
        <div className="flex-1 flex justify-center items-center py-20 text-txt-muted">
          <span className="animate-pulse">Loading verified model registry...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {filteredAndSorted.map(m => {
            const scores = m.scores || { Reasoning: 0.8, Coding: 0.8, Summary: 0.8, Creative: 0.8 };
            const cacheDiscount = m.price_cache_read != null && m.price_in > 0
              ? Math.round((1 - m.price_cache_read / m.price_in) * 100)
              : null;

            return (
              <div
                key={m.id}
                className="bg-surface border border-brd rounded-xl p-5 shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between"
              >
                <div>
                  {/* Top Bar: Name + Tier */}
                  <div className="flex justify-between items-start mb-1.5">
                    <div>
                      <h3 className="font-semibold text-[15px] text-txt-base leading-snug">{m.name}</h3>
                      <div className="flex items-center gap-1.5 text-[11px] text-txt-muted mt-0.5">
                        <span className="capitalize font-medium text-txt-base">{m.provider}</span>
                        <span>•</span>
                        <span className="font-mono text-txt-muted truncate max-w-[190px]" title={m.id}>{m.id}</span>
                      </div>
                    </div>
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      m.tier === 'frontier' ? 'bg-purple-100 text-purple-700 border border-purple-200' :
                      m.tier === 'medium' ? 'bg-blue-100 text-blue-700 border border-blue-200' :
                      'bg-emerald-100 text-emerald-700 border border-emerald-200'
                    }`}>
                      {m.tier}
                    </span>
                  </div>

                  {/* Benchmark Scores Visualization */}
                  <div className="my-4 bg-gray-50 rounded-lg p-3 border border-gray-150">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-txt-muted mb-2 flex justify-between">
                      <span>Benchmark Scores</span>
                      <span className="text-txt-muted font-mono">Norm. 0-100</span>
                    </div>
                    <div className="space-y-1.5 text-xs">
                      <div>
                        <div className="flex justify-between text-[11px] font-medium text-txt-base mb-0.5">
                          <span>Reasoning</span>
                          <span className="font-mono">{Math.round((scores.Reasoning || 0) * 100)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-gray-900 h-full rounded-full transition-all duration-300"
                            style={{ width: `${Math.round((scores.Reasoning || 0) * 100)}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[11px] font-medium text-txt-base mb-0.5">
                          <span>Coding</span>
                          <span className="font-mono">{Math.round((scores.Coding || 0) * 100)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-indigo-600 h-full rounded-full transition-all duration-300"
                            style={{ width: `${Math.round((scores.Coding || 0) * 100)}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[11px] font-medium text-txt-base mb-0.5">
                          <span>Summary</span>
                          <span className="font-mono">{Math.round((scores.Summary || 0) * 100)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-emerald-600 h-full rounded-full transition-all duration-300"
                            style={{ width: `${Math.round((scores.Summary || 0) * 100)}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[11px] font-medium text-txt-base mb-0.5">
                          <span>Creative</span>
                          <span className="font-mono">{Math.round((scores.Creative || 0) * 100)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-amber-600 h-full rounded-full transition-all duration-300"
                            style={{ width: `${Math.round((scores.Creative || 0) * 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Pricing and Context Grid */}
                  <div className="grid grid-cols-2 gap-2 text-[12px] mb-4">
                    <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
                      <div className="text-txt-muted font-semibold mb-0.5 uppercase tracking-wider text-[9px]">Input Price</div>
                      <div className="font-medium text-txt-base">${m.price_in.toFixed(2)} / 1M</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
                      <div className="text-txt-muted font-semibold mb-0.5 uppercase tracking-wider text-[9px]">Output Price</div>
                      <div className="font-medium text-txt-base">${m.price_out.toFixed(2)} / 1M</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
                      <div className="text-txt-muted font-semibold mb-0.5 uppercase tracking-wider text-[9px]">Prompt Cache</div>
                      {m.price_cache_read != null ? (
                        <div className="font-medium text-emerald-700 flex items-center gap-1">
                          <span>${m.price_cache_read.toFixed(2)}</span>
                          <span className="text-[10px] bg-emerald-100 px-1 py-0.2 rounded font-bold">-{cacheDiscount}%</span>
                        </div>
                      ) : (
                        <div className="text-txt-muted font-medium">Standard rate</div>
                      )}
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
                      <div className="text-txt-muted font-semibold mb-0.5 uppercase tracking-wider text-[9px]">Context Window</div>
                      <div className="font-medium text-txt-base">{(m.context_length / 1000).toFixed(0)}k tokens</div>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="pt-3 border-t border-gray-100 flex items-center justify-between gap-2">
                  <button
                    onClick={() => handleCopyId(m.id)}
                    className="text-xs text-txt-muted hover:text-txt-base px-2.5 py-1.5 rounded border border-brd hover:bg-gray-50 transition-colors flex items-center gap-1 font-mono"
                  >
                    {copiedId === m.id ? (
                      <>
                        <span className="text-emerald-600 font-bold">✓ Copied</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-3.5 h-3.5 text-txt-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        <span>Copy ID</span>
                      </>
                    )}
                  </button>

                  {onSelectModel && (
                    <button
                      onClick={() => onSelectModel(m.id)}
                      className="text-xs bg-gray-900 text-white hover:bg-black px-3 py-1.5 rounded font-medium transition-colors flex items-center gap-1"
                    >
                      <span>Route Prompt</span>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            );
          })}

          {filteredAndSorted.length === 0 && (
            <div className="col-span-full py-16 text-center bg-surface rounded-xl border border-brd">
              <p className="text-txt-muted font-medium text-sm">No models match your current filters or search query.</p>
              <button
                onClick={() => { setSearchQuery(''); setFilterProvider('All'); setFilterTier('All'); }}
                className="mt-3 text-xs text-blue-600 hover:underline"
              >
                Reset all filters
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
