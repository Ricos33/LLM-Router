import { useState, useEffect } from 'react';
import { getMetricsSummary, getModels } from '../api/client';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, ScatterChart, Scatter, ZAxis } from 'recharts';

const COLORS = { cheap: '#10b981', medium: '#3b82f6', frontier: '#8b5cf6' };

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [recent, setRecent] = useState([]);
  const [models, setModels] = useState([]);

  useEffect(() => {
    const fetchMetrics = () => {
      getMetricsSummary().then(setSummary).catch(console.warn);
      fetch(import.meta.env.VITE_API_URL || 'http://localhost:8000' + '/v1/metrics/recent?limit=10')
        .then(res => res.json())
        .then(setRecent)
        .catch(console.warn);
      getModels().then(setModels).catch(console.warn);
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 8000);
    return () => clearInterval(interval);
  }, []);

  if (!summary) return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-pulse flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-4 border-gray-200 border-t-black rounded-full animate-spin"></div>
        <div className="text-gray-400 text-sm font-medium">Loading telemetry...</div>
      </div>
    </div>
  );

  const tierDistribution = summary.tier_distribution || {
    cheap: summary.cheap_requests || 0,
    medium: summary.medium_requests || 0,
    frontier: summary.frontier_requests || 0,
  };

  const pieData = Object.entries(tierDistribution)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ 
      name: name.charAt(0).toUpperCase() + name.slice(1), 
      tierKey: name, 
      value 
    }));

  const costData = [
    { name: 'Actual', cost: summary.total_cost_actual || 0 },
    { name: 'Without Router', cost: summary.total_cost_if_frontier || 0 }
  ];

  const scatterData = models.map(m => ({
    name: m.name || m.id,
    price: m.price_in || 0.1,
    quality: (m.scores?.Reasoning || 0) * 100,
    context: m.context_length || 100000,
    tier: m.tier || 'cheap'
  }));

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 overflow-y-auto h-full text-[#111]">
      <div className="flex justify-between items-end pb-4 border-b border-gray-100">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Telemetry & Savings</h2>
          <p className="text-sm text-gray-500 mt-1">Real-time metrics from the LLM Router gateway</p>
        </div>
        <div className="text-xs font-semibold px-3 py-1 bg-green-100 text-green-700 rounded-full flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
          Live
        </div>
      </div>
      
      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white border border-gray-200 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
          <div className="text-[11px] font-bold text-gray-400 mb-2 uppercase tracking-widest flex items-center gap-2">
            <span>📉</span> Savings
          </div>
          <div className="text-3xl font-bold text-emerald-600">${(summary.total_cost_saved || 0).toFixed(2)}</div>
          <div className="mt-2 text-xs font-medium text-emerald-700 bg-emerald-50 inline-block px-2 py-0.5 rounded-md">
            -{summary.savings_percentage?.toFixed(1) || 0}% vs Frontier
          </div>
        </div>

        <div className="p-5 bg-white border border-gray-200 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
          <div className="text-[11px] font-bold text-gray-400 mb-2 uppercase tracking-widest flex items-center gap-2">
            <span>⚡</span> Avg Latency
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {(summary.avg_latency_ms || summary.average_latency_ms || 0).toFixed(0)} <span className="text-lg font-medium text-gray-400">ms</span>
          </div>
          <div className="mt-2 text-xs text-gray-500">Across all requests</div>
        </div>

        <div className="p-5 bg-white border border-gray-200 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
          <div className="text-[11px] font-bold text-gray-400 mb-2 uppercase tracking-widest flex items-center gap-2">
            <span>🎯</span> Total Requests
          </div>
          <div className="text-3xl font-bold text-gray-900">{summary.total_requests}</div>
          <div className="mt-2 text-xs text-gray-500">{(summary.total_tokens || 0).toLocaleString()} tokens processed</div>
        </div>

        <div className="p-5 bg-white border border-gray-200 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
          <div className="text-[11px] font-bold text-gray-400 mb-2 uppercase tracking-widest flex items-center gap-2">
            <span>🏎️</span> Offloaded
          </div>
          <div className="text-3xl font-bold text-blue-600">
            {summary.cheap_percentage || 0}<span className="text-lg font-medium text-blue-400">%</span>
          </div>
          <div className="mt-2 text-xs text-blue-700 bg-blue-50 inline-block px-2 py-0.5 rounded-md">
            Routed to Cheap tier
          </div>
        </div>
      </div>

      {summary.monthly_budget_usd > 0 && (
        <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
          <div className="flex justify-between items-end mb-2">
            <div className="text-[11px] font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
              <span>💳</span> Monthly Budget Tracking
            </div>
            <div className="text-[13px] font-medium text-gray-600">
              ${summary.current_month_cost?.toFixed(2) || 0} / ${summary.monthly_budget_usd?.toFixed(2)}
            </div>
          </div>
          <div className="h-3 w-full bg-gray-100 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 rounded-full ${summary.current_month_cost > summary.monthly_budget_usd * 0.9 ? 'bg-red-500' : 'bg-emerald-500'}`}
              style={{ width: `${Math.min(100, (summary.current_month_cost / summary.monthly_budget_usd) * 100)}%` }}
            ></div>
          </div>
          <div className="mt-2 flex justify-between text-[11px] text-gray-400">
            <span>0%</span>
            <span>{((summary.current_month_cost / summary.monthly_budget_usd) * 100).toFixed(1)}% used</span>
            <span>100%</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tier Distribution Chart */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <h3 className="text-sm font-semibold mb-6 flex items-center gap-2">
            Tier Distribution
          </h3>
          {pieData.length > 0 ? (
            <div className="h-64 relative">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={70} outerRadius={90} paddingAngle={5} dataKey="value" stroke="none">
                    {pieData.map((e, i) => <Cell key={i} fill={COLORS[e.tierKey] || '#999'} />)}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                    itemStyle={{ fontSize: '13px', fontWeight: '500' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none flex-col">
                <span className="text-2xl font-bold">{summary.total_requests}</span>
                <span className="text-[10px] uppercase text-gray-400 font-bold tracking-wider">Reqs</span>
              </div>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-sm text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-200">No routing data available</div>
          )}
        </div>

        {/* Value vs Cost Scatter Chart */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <h3 className="text-sm font-semibold mb-6">Value (Reasoning) vs Cost</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                <XAxis type="number" dataKey="price" name="Cost ($/M)" unit="$" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} />
                <YAxis type="number" dataKey="quality" name="Quality" domain={[60, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} />
                <ZAxis type="number" dataKey="context" range={[50, 400]} />
                <Tooltip 
                  cursor={{ strokeDasharray: '3 3' }}
                  contentStyle={{ borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', fontSize: '13px', padding: '10px' }}
                  formatter={(value, name) => [name === 'Cost ($/M)' ? `$${value}` : `${value.toFixed(1)}`, name]}
                  labelFormatter={() => ''}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-white p-3 border border-gray-200 rounded-xl shadow-lg">
                          <p className="font-bold text-sm mb-1">{data.name}</p>
                          <p className="text-xs text-gray-500">Tier: <span className="font-semibold">{data.tier}</span></p>
                          <p className="text-xs text-gray-500">Cost (In): <span className="font-semibold text-emerald-600">${data.price}/M</span></p>
                          <p className="text-xs text-gray-500">Reasoning: <span className="font-semibold text-blue-600">{data.quality.toFixed(1)}</span></p>
                          <p className="text-xs text-gray-500">Context: <span className="font-semibold">{data.context.toLocaleString()}</span></p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Scatter name="Models" data={scatterData} fill="#8884d8">
                  {scatterData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.tier] || '#999'} fillOpacity={0.7} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      
      {/* Recent Requests Table */}
      <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden mt-6">
        <div className="p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <span>📋</span> Recent Requests
          </h3>
          <a
            href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/v1/metrics/export/csv`}
            download="llm_router_metrics.csv"
            className="px-3 py-1.5 bg-white border border-gray-200 rounded-md text-[12px] font-semibold text-gray-700 hover:bg-gray-50 transition-colors shadow-sm flex items-center gap-1.5"
          >
            <span>📥</span> Export CSV
          </a>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-white text-[11px] uppercase tracking-wider text-gray-400 font-semibold border-b border-gray-100">
              <tr>
                <th className="px-5 py-3 w-1/4">Prompt Preview</th>
                <th className="px-5 py-3">Tier</th>
                <th className="px-5 py-3">Model</th>
                <th className="px-5 py-3 text-right">Score</th>
                <th className="px-5 py-3 text-right">Latency</th>
                <th className="px-5 py-3 text-right">Cost</th>
                <th className="px-5 py-3 text-right">Saved</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {recent.length > 0 ? recent.map((req, i) => (
                <tr key={i} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3 font-medium text-gray-900 truncate max-w-[200px]" title={req.prompt_preview}>
                    {req.prompt_preview || 'Empty prompt'}
                  </td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold tracking-wide uppercase ${
                      req.routed_tier === 'frontier' ? 'bg-purple-100 text-purple-700' :
                      req.routed_tier === 'medium' ? 'bg-blue-100 text-blue-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {req.routed_tier}
                    </span>
                  </td>
                  <td className="px-5 py-3 font-mono text-[12px] truncate max-w-[150px]">{req.actual_model}</td>
                  <td className="px-5 py-3 text-right font-mono text-[12px] text-gray-500">{(req.classifier_score || 0).toFixed(2)}</td>
                  <td className="px-5 py-3 text-right font-mono text-[12px]">{Math.round(req.latency_ms)}ms</td>
                  <td className="px-5 py-3 text-right font-mono text-[12px]">${(req.cost_actual || 0).toFixed(4)}</td>
                  <td className="px-5 py-3 text-right font-mono text-[12px] text-emerald-600 font-medium">${(req.cost_saved_usd || 0).toFixed(4)}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="5" className="px-5 py-8 text-center text-gray-400">No requests yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
