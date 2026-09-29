import { useState, useEffect, Fragment } from 'react';
import {
  getMetricsSummary,
  getModels,
  getBudgetStatus,
  testBudgetAlert,
  configureBudget,
  clearBudgetAlerts,
} from '../api/client';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, ScatterChart, Scatter, ZAxis } from 'recharts';

const COLORS = { cheap: '#10b981', medium: '#3b82f6', frontier: '#8b5cf6' };

const AUTHORIZED_PROVIDERS = ['anthropic', 'openai', 'google', 'qwen', 'mistral', 'deepseek', 'meta', 'xai'];

export default function Dashboard({ onReplayPrompt }) {
  const [summary, setSummary] = useState(null);
  const [recent, setRecent] = useState([]);
  const [models, setModels] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [providerHealth, setProviderHealth] = useState({});
  const [timeseriesMetric, setTimeseriesMetric] = useState('requests');
  const [tierFilter, setTierFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedRow, setExpandedRow] = useState(null);
  const [chaosLoading, setChaosLoading] = useState(false);
  const [chaosFeedback, setChaosFeedback] = useState(null);

  // Enterprise Budget State
  const [budgetStatus, setBudgetStatus] = useState(null);
  const [budgetDrawerOpen, setBudgetDrawerOpen] = useState(false);
  const [budgetForm, setBudgetForm] = useState({ monthly_budget_usd: '', webhook_url: '' });
  const [budgetActionLoading, setBudgetActionLoading] = useState(false);
  const [budgetFeedback, setBudgetFeedback] = useState(null);

  // Live Probing State
  const [probing, setProbing] = useState(false);

  const handleProbeProviders = async () => {
    setProbing(true);
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(`${apiUrl}/v1/providers/probe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        setProviderHealth(data.all_health);
        setChaosFeedback(`Probed ${data.total_probed} providers: ${data.healthy_count} healthy.`);
        setTimeout(() => setChaosFeedback(null), 5000);
      }
    } catch (e) {
      console.warn(e);
    } finally {
      setProbing(false);
    }
  };

  const handleTripProvider = async (provider) => {
    setChaosLoading(true);
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(`${apiUrl}/v1/chaos/trip`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, reason: `Manual simulated outage on ${provider}` }),
      });
      if (res.ok) {
        const data = await res.json();
        setProviderHealth(data.all_health);
        setChaosFeedback(`Simulated outage active for ${provider}. Traffic will fail over automatically.`);
        setTimeout(() => setChaosFeedback(null), 6000);
      }
    } catch (e) {
      console.warn(e);
    } finally {
      setChaosLoading(false);
    }
  };

  const handleResetProvider = async (provider = 'all') => {
    setChaosLoading(true);
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(`${apiUrl}/v1/chaos/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      });
      if (res.ok) {
        const data = await res.json();
        setProviderHealth(data.all_health);
        setChaosFeedback(provider === 'all' ? 'All provider circuits reset to healthy.' : `${provider} circuit restored.`);
        setTimeout(() => setChaosFeedback(null), 4000);
      }
    } catch (e) {
      console.warn(e);
    } finally {
      setChaosLoading(false);
    }
  };

  const handleTestAlert = async () => {
    setBudgetActionLoading(true);
    try {
      const res = await testBudgetAlert();
      setBudgetFeedback(
        res.webhook_tested
          ? (res.webhook_dispatched ? 'Synthetic alert dispatched to webhook!' : 'Test alert generated (webhook HTTP error).')
          : 'Synthetic test alert recorded in history.'
      );
      getBudgetStatus().then(setBudgetStatus).catch(console.warn);
      setTimeout(() => setBudgetFeedback(null), 5000);
    } catch (e) {
      setBudgetFeedback('Failed to trigger test alert: ' + (e.message || e));
    } finally {
      setBudgetActionLoading(false);
    }
  };

  const handleUpdateBudget = async (e) => {
    e.preventDefault();
    setBudgetActionLoading(true);
    try {
      const payload = {};
      if (budgetForm.monthly_budget_usd !== '') {
        payload.monthly_budget_usd = parseFloat(budgetForm.monthly_budget_usd);
      }
      if (budgetForm.webhook_url !== '') {
        payload.webhook_url = budgetForm.webhook_url;
      }
      await configureBudget(payload);
      const updated = await getBudgetStatus();
      setBudgetStatus(updated);
      setBudgetDrawerOpen(false);
      setBudgetFeedback('Budget settings updated successfully.');
      setTimeout(() => setBudgetFeedback(null), 4000);
    } catch (e) {
      setBudgetFeedback('Failed to update budget: ' + (e.message || e));
    } finally {
      setBudgetActionLoading(false);
    }
  };

  const handleClearAlerts = async () => {
    try {
      await clearBudgetAlerts();
      const updated = await getBudgetStatus();
      setBudgetStatus(updated);
      setBudgetFeedback('Budget alerts cleared.');
      setTimeout(() => setBudgetFeedback(null), 3000);
    } catch (e) {
      console.warn(e);
    }
  };

  useEffect(() => {
    const fetchMetrics = () => {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      getMetricsSummary().then(setSummary).catch(console.warn);
      getBudgetStatus().then(setBudgetStatus).catch(console.warn);
      fetch(`${apiUrl}/v1/metrics/recent?limit=50`)
        .then(res => res.json())
        .then(setRecent)
        .catch(console.warn);
      fetch(`${apiUrl}/v1/analytics`)
        .then(res => res.json())
        .then(setAnalytics)
        .catch(console.warn);
      fetch(`${apiUrl}/v1/providers/health`)
        .then(res => res.json())
        .then(setProviderHealth)
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

  const hourlyData = (analytics?.hourly_timeseries || []).map(h => {
    const d = new Date(h.hour_ts * 1000);
    return {
      hour: `${d.getHours().toString().padStart(2, '0')}:00`,
      requests: h.requests,
      saved: Number((h.saved || 0).toFixed(4)),
      cost: Number((h.cost || 0).toFixed(4))
    };
  });

  const filteredRecent = recent.filter(req => {
    const matchesTier = tierFilter === 'all' || req.routed_tier?.toLowerCase() === tierFilter.toLowerCase();
    const query = searchQuery.trim().toLowerCase();
    const matchesSearch = !query || 
      (req.prompt_preview || '').toLowerCase().includes(query) ||
      (req.actual_model || '').toLowerCase().includes(query);
    return matchesTier && matchesSearch;
  });

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
            <span>🛡️</span> Optimization Rate
          </div>
          <div className="text-3xl font-bold text-blue-600">
            {analytics?.efficiency_percentage !== undefined ? analytics.efficiency_percentage : (summary.cheap_percentage || 0)}<span className="text-lg font-medium text-blue-400">%</span>
          </div>
          <div className="mt-2 text-xs text-blue-700 bg-blue-50 inline-block px-2 py-0.5 rounded-md">
            Non-frontier optimized
          </div>
        </div>
      </div>

      {/* Enterprise Budget & Threshold Alerting Hub */}
      <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <div className="flex items-center gap-2.5">
            <span className="text-lg">💳</span>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Enterprise Budget & Alerts</h3>
              <p className="text-[11px] text-gray-500">Monthly spend threshold monitoring & automated webhooks</p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Status Badge */}
            {budgetStatus?.status === 'unlimited' ? (
              <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700 border border-gray-200">
                Unlimited Tier
              </span>
            ) : budgetStatus?.status === 'critical' ? (
              <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-700 border border-red-200 flex items-center gap-1.5 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span> Budget Exceeded
              </span>
            ) : budgetStatus?.status === 'warning' ? (
              <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-800 border border-amber-200 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span> Warning (80%+)
              </span>
            ) : budgetStatus?.status === 'caution' ? (
              <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 border border-blue-200">
                Caution (50%+)
              </span>
            ) : (
              <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> Spend Normal
              </span>
            )}

            {/* Webhook Status */}
            <span className={`px-2 py-0.5 text-[11px] rounded border ${budgetStatus?.webhook_configured ? 'bg-purple-50 text-purple-700 border-purple-200' : 'bg-gray-50 text-gray-400 border-gray-200'}`}>
              {budgetStatus?.webhook_configured ? '🔔 Webhook Active' : '🔕 Webhook Unset'}
            </span>

            {/* Action Buttons */}
            <button
              onClick={handleTestAlert}
              disabled={budgetActionLoading}
              className="px-2.5 py-1 text-xs font-medium bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200 rounded-lg transition-colors flex items-center gap-1 shadow-2xs"
              title="Send a synthetic test alert"
            >
              ⚡ Test Alert
            </button>

            <button
              onClick={() => {
                if (budgetStatus) {
                  setBudgetForm({
                    monthly_budget_usd: budgetStatus.monthly_budget_usd || '',
                    webhook_url: budgetStatus.webhook_url || '',
                  });
                }
                setBudgetDrawerOpen(!budgetDrawerOpen);
              }}
              className="px-2.5 py-1 text-xs font-medium bg-black text-white hover:bg-gray-800 rounded-lg transition-colors shadow-2xs"
            >
              {budgetDrawerOpen ? 'Close' : '⚙️ Configure'}
            </button>
          </div>
        </div>

        {/* Feedback message */}
        {budgetFeedback && (
          <div className="text-xs p-2.5 bg-gray-50 border border-gray-200 rounded-lg text-gray-800 animate-in fade-in flex items-center justify-between">
            <span>{budgetFeedback}</span>
            <button onClick={() => setBudgetFeedback(null)} className="text-gray-400 hover:text-black">✕</button>
          </div>
        )}

        {/* Inline Config Drawer */}
        {budgetDrawerOpen && (
          <form onSubmit={handleUpdateBudget} className="p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-3 animate-in fade-in">
            <div className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Update Budget & Alert Settings</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-gray-600 mb-1">Monthly Budget (USD, 0 = unlimited)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="e.g. 50.00"
                  value={budgetForm.monthly_budget_usd}
                  onChange={e => setBudgetForm({ ...budgetForm, monthly_budget_usd: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs bg-white border border-gray-200 rounded-lg outline-none focus:border-black font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-gray-600 mb-1">Alert Webhook URL (Slack, Discord, PagerDuty)</label>
                <input
                  type="url"
                  placeholder="https://hooks.slack.com/services/..."
                  value={budgetForm.webhook_url}
                  onChange={e => setBudgetForm({ ...budgetForm, webhook_url: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs bg-white border border-gray-200 rounded-lg outline-none focus:border-black font-mono"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setBudgetDrawerOpen(false)}
                className="px-3 py-1 text-xs text-gray-500 hover:text-black"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={budgetActionLoading}
                className="px-4 py-1 text-xs font-medium bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
              >
                Save Settings
              </button>
            </div>
          </form>
        )}

        {/* Progress and Stats Row */}
        {budgetStatus && budgetStatus.monthly_budget_usd > 0 ? (
          <div>
            <div className="flex justify-between items-end text-xs mb-1.5">
              <span className="font-semibold text-gray-700">
                ${budgetStatus.current_cost_usd?.toFixed(2) || '0.00'}{' '}
                <span className="font-normal text-gray-400">/ ${budgetStatus.monthly_budget_usd?.toFixed(2)} monthly cap</span>
              </span>
              <span className="text-gray-500 font-mono text-[11px]">
                {budgetStatus.remaining_usd !== null && `$${budgetStatus.remaining_usd?.toFixed(2)} remaining`} ({budgetStatus.percent_used?.toFixed(1)}%)
              </span>
            </div>

            <div className="h-2.5 w-full bg-gray-100 rounded-full overflow-hidden relative">
              <div
                className={`h-full transition-all duration-500 rounded-full ${
                  budgetStatus.percent_used >= 100
                    ? 'bg-red-500'
                    : budgetStatus.percent_used >= 80
                    ? 'bg-amber-500'
                    : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(100, budgetStatus.percent_used || 0)}%` }}
              ></div>
            </div>

            <div className="flex justify-between text-[10px] text-gray-400 font-mono mt-1">
              <span>0%</span>
              <span className="text-blue-500">50% Notice</span>
              <span className="text-amber-500">80% Warning</span>
              <span className="text-red-500">100% Limit</span>
            </div>
          </div>
        ) : (
          <div className="p-3 bg-gray-50 rounded-xl border border-dashed border-gray-200 flex items-center justify-between text-xs text-gray-500">
            <span>No monthly cap configured. Current cycle cost: <strong className="text-gray-800 font-mono">${(summary?.current_month_cost || 0).toFixed(4)}</strong></span>
            <button
              onClick={() => {
                setBudgetForm({ monthly_budget_usd: '25.00', webhook_url: '' });
                setBudgetDrawerOpen(true);
              }}
              className="text-xs font-semibold text-black hover:underline"
            >
              + Set Cap
            </button>
          </div>
        )}

        {/* Recent Alert Events Log */}
        {budgetStatus?.recent_alerts && budgetStatus.recent_alerts.length > 0 && (
          <div className="pt-2 border-t border-gray-100">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                Recent Alert History ({budgetStatus.alert_count})
              </span>
              <button
                onClick={handleClearAlerts}
                className="text-[11px] text-gray-400 hover:text-red-600 transition-colors"
              >
                Clear History
              </button>
            </div>
            <div className="flex flex-col gap-1.5 max-h-32 overflow-y-auto">
              {budgetStatus.recent_alerts.slice(0, 5).map((a, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-gray-50 text-[11px] border border-gray-100 font-mono">
                  <span className="text-gray-700 truncate mr-2">{a.message}</span>
                  <span className="text-gray-400 flex-shrink-0">
                    {new Date(a.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

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

      {/* Provider Circuit Health Grid */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <span>🛡️</span> Upstream Provider Circuit Health
              </h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
                Chaos Ready
              </span>
            </div>
            <p className="text-[11px] text-gray-400 font-medium mt-0.5">
              Automatic failover & half-open probing. Simulate upstream provider failure to observe live failover.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleProbeProviders}
              disabled={probing || chaosLoading}
              className="text-xs px-2.5 py-1 bg-black text-white hover:bg-gray-800 rounded-lg font-medium transition-colors flex items-center gap-1 shadow-2xs disabled:opacity-50"
              title="Probe roundtrip ping and update latency stats across all providers"
            >
              {probing ? 'Probing...' : '⚡ Probe All'}
            </button>
            {Object.values(providerHealth).some(h => h.status === 'tripped') && (
              <button
                onClick={() => handleResetProvider('all')}
                disabled={chaosLoading}
                className="text-xs px-2.5 py-1 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 rounded-lg font-medium transition-colors"
              >
                ↺ Reset Circuits
              </button>
            )}
            <span className="text-xs px-2.5 py-0.5 bg-gray-100 rounded-full font-mono text-gray-600 font-medium">
              8 Providers
            </span>
          </div>
        </div>

        {chaosFeedback && (
          <div className="mb-4 text-xs font-medium px-3.5 py-2 rounded-xl bg-purple-50 text-purple-800 border border-purple-200 flex items-center justify-between animate-in fade-in">
            <div className="flex items-center gap-2">
              <span>⚡</span>
              <span>{chaosFeedback}</span>
            </div>
            <button
              onClick={() => setChaosFeedback(null)}
              className="text-purple-400 hover:text-purple-700 text-sm font-bold"
            >
              ×
            </button>
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          {AUTHORIZED_PROVIDERS.map(p => {
            const h = providerHealth[p] || { status: 'healthy', consecutive_failures: 0 };
            const isTripped = h.status === 'tripped';
            const isDegraded = h.status === 'degraded';
            return (
              <div 
                key={p} 
                className={`p-3 rounded-xl border flex flex-col items-center justify-between text-center transition-all ${
                  isTripped ? 'border-red-300 bg-red-50/60 shadow-xs ring-1 ring-red-200' :
                  isDegraded ? 'border-amber-200 bg-amber-50/50' :
                  'border-gray-200 bg-gray-50/40 hover:border-gray-300'
                }`}
              >
                <div>
                  <div className="flex items-center justify-center gap-1.5 mb-1">
                    <span className={`w-2 h-2 rounded-full ${
                      isTripped ? 'bg-red-500 animate-pulse' :
                      isDegraded ? 'bg-amber-500' :
                      'bg-emerald-500'
                    }`} />
                    <span className="text-xs font-semibold capitalize text-gray-800">{p}</span>
                  </div>
                  <span className={`text-[10px] font-bold uppercase tracking-wider block ${
                    isTripped ? 'text-red-700' :
                    isDegraded ? 'text-amber-700' :
                    'text-emerald-700'
                  }`}>
                    {h.status}
                  </span>
                  <div className="mt-1 flex flex-col gap-0.5 text-[10px] font-mono text-gray-500">
                    <span title="Latest / Avg Latency">
                      ⏱️ {h.latest_latency_ms ? `${h.latest_latency_ms}ms` : (h.avg_latency_ms ? `${h.avg_latency_ms}ms` : '—')}
                    </span>
                    <span className="text-[9px] text-gray-400">
                      {h.availability_rate_pct !== undefined ? `${h.availability_rate_pct}% avail` : (h.consecutive_failures > 0 ? `${h.consecutive_failures} errs` : '100% avail')}
                    </span>
                  </div>
                </div>
                <div className="mt-2.5 pt-2 border-t border-gray-100 w-full flex justify-center">
                  {isTripped ? (
                    <button
                      onClick={() => handleResetProvider(p)}
                      disabled={chaosLoading}
                      title="Reset circuit breaker to healthy"
                      className="text-[10px] font-bold text-emerald-700 bg-emerald-100 hover:bg-emerald-200 px-2 py-0.5 rounded transition-all shadow-2xs"
                    >
                      ↺ Restore
                    </button>
                  ) : (
                    <button
                      onClick={() => handleTripProvider(p)}
                      disabled={chaosLoading}
                      title="Simulate outage for chaos testing"
                      className="text-[10px] font-medium text-gray-400 hover:text-red-600 hover:bg-red-50 px-1.5 py-0.5 rounded transition-colors"
                    >
                      ⚡ Trip Outage
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Hourly Activity & Top Models Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Hourly Timeseries Chart */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <span>📈</span> 24h Routing Activity
            </h3>
            <div className="flex bg-gray-100 rounded-lg p-0.5 text-[11px] font-semibold">
              <button
                onClick={() => setTimeseriesMetric('requests')}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  timeseriesMetric === 'requests' ? 'bg-white shadow-xs text-black' : 'text-gray-500 hover:text-black'
                }`}
              >
                Requests
              </button>
              <button
                onClick={() => setTimeseriesMetric('saved')}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  timeseriesMetric === 'saved' ? 'bg-white shadow-xs text-emerald-600' : 'text-gray-500 hover:text-black'
                }`}
              >
                Saved ($)
              </button>
            </div>
          </div>
          {hourlyData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={hourlyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                  <XAxis dataKey="hour" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#6b7280' }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#6b7280' }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', fontSize: '13px' }}
                    formatter={(val) => [timeseriesMetric === 'saved' ? `$${Number(val).toFixed(4)}` : val, timeseriesMetric === 'saved' ? 'Cost Saved' : 'Requests']}
                  />
                  <Bar
                    dataKey={timeseriesMetric}
                    fill={timeseriesMetric === 'saved' ? '#10b981' : '#111827'}
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-sm text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-200 gap-2">
              <span className="text-xl">⏱️</span>
              <span>No requests recorded in the last 24h</span>
            </div>
          )}
        </div>

        {/* Top Models Performance Matrix */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <span>🏆</span> Model Distribution & Performance
              </h3>
              <span className="text-xs text-gray-400 font-mono">{(analytics?.model_stats || []).length} models routed</span>
            </div>
            {(analytics?.model_stats || []).length > 0 ? (
              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                {(analytics.model_stats).slice(0, 5).map((m, idx) => {
                  const sharePct = summary.total_requests > 0 ? Math.round((m.count / summary.total_requests) * 100) : 0;
                  return (
                    <div key={idx} className="p-3 bg-gray-50 rounded-xl border border-gray-100 flex flex-col gap-1.5">
                      <div className="flex justify-between items-center text-[12px]">
                        <span className="font-semibold text-gray-800 truncate max-w-[200px]" title={m.model_used}>
                          {m.model_used}
                        </span>
                        <div className="flex items-center gap-2 font-mono">
                          <span className="text-gray-500 font-bold">{m.count} reqs</span>
                          <span className="text-gray-400">({sharePct}%)</span>
                        </div>
                      </div>
                      <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                        <div className="h-full bg-black rounded-full" style={{ width: `${Math.max(4, sharePct)}%` }} />
                      </div>
                      <div className="flex justify-between text-[11px] text-gray-400 font-mono mt-0.5">
                        <span>Avg Latency: <strong className="text-gray-600">{Math.round(m.avg_latency)}ms</strong></span>
                        <span>Avg Score: <strong className="text-gray-600">{(m.avg_score || 0).toFixed(2)}</strong></span>
                        <span>Avg Cost: <strong className="text-emerald-600">${(m.avg_cost || 0).toFixed(4)}</strong></span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-sm text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-200 gap-2">
                <span className="text-xl">📊</span>
                <span>No model performance data yet</span>
              </div>
            )}
          </div>
          <div className="text-[11px] text-gray-400 pt-3 border-t border-gray-100 mt-2">
            Statistics dynamically calculated from actual completions telemetry.
          </div>
        </div>
      </div>

      {/* Provider Distribution & Prompt Caching Economics Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Provider Traffic Distribution */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <span>🌐</span> Upstream Provider Traffic
            </h3>
            <span className="text-xs text-gray-400 font-mono">
              {(analytics?.provider_stats || []).length} active providers
            </span>
          </div>

          {(analytics?.provider_stats || []).length > 0 ? (
            <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
              {(analytics.provider_stats).map((p, idx) => {
                const totalReqs = summary.total_requests || 1;
                const pct = Math.round((p.requests / totalReqs) * 100);
                return (
                  <div key={idx} className="p-3 bg-gray-50 rounded-xl border border-gray-100 flex flex-col gap-1.5">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-semibold capitalize text-gray-800">{p.provider}</span>
                      <div className="flex items-center gap-2 font-mono">
                        <span className="text-gray-600 font-medium">{p.requests} reqs</span>
                        <span className="text-gray-400">({pct}%)</span>
                        <span className="text-emerald-600 font-semibold">${p.total_cost.toFixed(4)}</span>
                      </div>
                    </div>
                    <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full bg-purple-600 rounded-full" style={{ width: `${Math.max(3, pct)}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="h-44 flex flex-col items-center justify-center text-xs text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-200">
              No multi-provider traffic logged yet.
            </div>
          )}
        </div>

        {/* Prompt Caching Economics & Savings Card */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <span>⚡</span> Prompt Caching Economics
              </h3>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                Up to 90% Savings
              </span>
            </div>
            
            <p className="text-xs text-gray-500 mb-4 leading-relaxed">
              When repetitive context (system instructions, codebases, documents) is reused, modern providers offer steep cache read discounts.
            </p>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                <div className="text-[11px] text-gray-400 uppercase font-semibold">Total Prompt Tokens</div>
                <div className="text-lg font-bold text-gray-900 font-mono mt-1">
                  {(analytics?.prompt_cache_analytics?.total_prompt_tokens || 0).toLocaleString()}
                </div>
              </div>
              <div className="p-3 bg-emerald-50/60 rounded-xl border border-emerald-100">
                <div className="text-[11px] text-emerald-700 uppercase font-semibold">Projected Cache Savings</div>
                <div className="text-lg font-bold text-emerald-600 font-mono mt-1">
                  ${(analytics?.prompt_cache_analytics?.projected_cache_savings_usd || 0).toFixed(4)}
                </div>
              </div>
            </div>

            <div className="p-3 mb-4 bg-amber-50/60 rounded-xl border border-amber-100 flex items-center justify-between">
              <div>
                <div className="text-[11px] text-amber-700 uppercase font-semibold">Resilience Fallbacks</div>
                <div className="text-xs text-amber-600 mt-0.5">Transparent recovery rate on upstream failure</div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-amber-600 font-mono">
                  {analytics?.resilience_stats?.total_fallbacks || 0} <span className="text-[11px] text-amber-500 font-sans">events</span>
                </div>
                <div className="text-[10px] text-amber-600 font-semibold">{analytics?.resilience_stats?.fallback_rate_pct || 0}% rate</div>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Provider Cache Discounts:</div>
              <div className="flex flex-wrap gap-1.5 text-[11px]">
                <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-700">Anthropic: <strong>-90%</strong></span>
                <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-700">DeepSeek: <strong>-90%</strong></span>
                <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-700">Qwen: <strong>-80%</strong></span>
                <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-700">Meta: <strong>-80%</strong></span>
                <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-700">Google: <strong>-75%</strong></span>
                <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-700">OpenAI: <strong>-50%</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Recent Requests Table */}
      <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden mt-6">
        <div className="p-4 border-b border-gray-100 flex flex-wrap gap-3 justify-between items-center bg-gray-50/50">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <span>📋</span> Recent Requests
            </h3>
            <span className="text-xs bg-gray-200/70 text-gray-600 px-2 py-0.5 rounded-full font-mono">
              {filteredRecent.length} / {recent.length}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Tier Filter Pills */}
            <div className="flex bg-white border border-gray-200 rounded-lg p-0.5 text-[11px] font-medium shadow-2xs">
              {['all', 'cheap', 'medium', 'frontier'].map(t => (
                <button
                  key={t}
                  onClick={() => setTierFilter(t)}
                  className={`px-2 py-0.5 rounded capitalize transition-colors ${
                    tierFilter === t ? 'bg-black text-white font-semibold' : 'text-gray-500 hover:text-black'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search prompt or model..."
                className="px-2.5 py-1 text-xs bg-white border border-gray-200 rounded-lg focus:outline-none focus:border-black w-44 transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1 text-gray-400 hover:text-black text-xs"
                >
                  ×
                </button>
              )}
            </div>

            <a
              href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/v1/metrics/export/csv`}
              download="llm_router_metrics.csv"
              className="px-2.5 py-1 bg-white border border-gray-200 rounded-lg text-[11px] font-semibold text-gray-700 hover:bg-gray-50 transition-colors shadow-2xs flex items-center gap-1"
            >
              <span>📥</span> CSV
            </a>
            <a
              href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/v1/metrics/export/json`}
              download="llm_router_metrics.json"
              className="px-2.5 py-1 bg-white border border-gray-200 rounded-lg text-[11px] font-semibold text-gray-700 hover:bg-gray-50 transition-colors shadow-2xs flex items-center gap-1"
            >
              <span>📄</span> JSON
            </a>
            <button
              onClick={async () => {
                if (window.confirm('Are you sure you want to delete all analytics data? This cannot be undone.')) {
                  try {
                    const apiBase = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                    await fetch(`${apiBase}/v1/analytics`, { method: 'DELETE' });
                    window.location.reload();
                  } catch (e) {
                    alert('Error clearing analytics');
                  }
                }
              }}
              className="px-2.5 py-1 bg-red-50 border border-red-200 rounded-lg text-[11px] font-semibold text-red-600 hover:bg-red-100 hover:text-red-700 transition-colors shadow-2xs flex items-center gap-1 ml-2"
            >
              <span>🗑️</span> Clear
            </button>
          </div>
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
                <th className="px-4 py-3 text-center">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filteredRecent.length > 0 ? filteredRecent.map((req, i) => (
                <Fragment key={i}>
                  <tr 
                    onClick={() => setExpandedRow(expandedRow === i ? null : i)}
                    className="hover:bg-gray-50 transition-colors cursor-pointer"
                  >
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
                    <td className="px-4 py-3 text-center" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          onClick={() => setExpandedRow(expandedRow === i ? null : i)}
                          title="Toggle details"
                          className="px-2 py-1 text-[11px] font-medium text-gray-600 border border-gray-200 rounded hover:bg-white transition-colors"
                        >
                          {expandedRow === i ? '▲' : '▼'}
                        </button>
                        <button
                          onClick={() => navigator.clipboard.writeText(req.prompt_preview || '')}
                          title="Copy prompt"
                          className="px-2 py-1 text-[11px] text-gray-500 hover:text-black border border-gray-200 rounded hover:bg-white transition-colors"
                        >
                          Copy
                        </button>
                        {onReplayPrompt && (
                          <button
                            onClick={() => onReplayPrompt(req.prompt_preview || '')}
                            title="Replay in Playground"
                            className="px-2 py-1 text-[11px] font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded transition-colors"
                          >
                            Replay ↗
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {expandedRow === i && (
                    <tr className="bg-gray-50/80">
                      <td colSpan="8" className="p-4 border-t border-gray-100">
                        <div className="flex flex-col gap-2.5 text-xs text-gray-700">
                          <div className="font-semibold text-gray-900 flex justify-between items-center">
                            <span>Full Prompt Preview:</span>
                            <span className="font-mono text-[11px] text-gray-400">
                              {req.timestamp ? new Date(req.timestamp * 1000).toLocaleString() : ''}
                            </span>
                          </div>
                          <p className="bg-white p-3 rounded-lg border border-gray-200 font-mono text-xs whitespace-pre-wrap leading-relaxed text-gray-800">
                            {req.prompt_preview || 'Empty prompt'}
                          </p>
                          <div className="flex flex-wrap gap-4 text-[11px] font-mono text-gray-500 pt-1">
                            <span>Tokens: <strong className="text-gray-800">{req.prompt_tokens || 0}</strong> in / <strong className="text-gray-800">{req.completion_tokens || 0}</strong> out (Total: {req.total_tokens || 0})</span>
                            <span>Actual Cost: <strong className="text-gray-800">${(req.cost_actual || 0).toFixed(5)}</strong></span>
                            <span>Frontier Baseline: <strong className="text-gray-400 line-through">${(req.cost_if_frontier || 0).toFixed(5)}</strong></span>
                            <span>Net Saved: <strong className="text-emerald-600">${(req.cost_saved || req.cost_saved_usd || 0).toFixed(5)}</strong></span>
                          </div>
                          {req.classifier_reasons && (
                            <div className="flex flex-wrap gap-1.5 items-center mt-1">
                              <span className="text-[11px] font-medium text-gray-400 mr-1">Classification Signals:</span>
                              {(typeof req.classifier_reasons === 'string' ? JSON.parse(req.classifier_reasons || '[]') : req.classifier_reasons).map((reason, rIdx) => (
                                <span key={rIdx} className="bg-white border border-gray-200 text-gray-700 px-2 py-0.5 rounded text-[10px] font-medium">
                                  {reason}
                                </span>
                              ))}
                            </div>
                          )}
                          {onReplayPrompt && (
                            <div className="pt-2">
                              <button
                                onClick={() => onReplayPrompt(req.prompt_preview || '')}
                                className="text-xs bg-black text-white hover:bg-gray-800 px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 shadow-xs"
                              >
                                <span>Replay & Route in Playground</span>
                                <span>→</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )) : (
                <tr>
                  <td colSpan="8" className="px-5 py-8 text-center text-gray-400">
                    {recent.length === 0 ? 'No requests recorded yet' : 'No requests matching filters'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
