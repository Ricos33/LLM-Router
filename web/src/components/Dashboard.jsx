import { useState, useEffect, useCallback } from 'react';
import { getMetricsSummary, getRecentMetrics } from '../api/client';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import {
  Activity,
  DollarSign,
  Clock,
  Hash,
  Zap,
  Shield,
  Sparkles,
  AlertTriangle,
  RefreshCw,
  ArrowRight,
  Layers,
  Database,
  Terminal,
} from 'lucide-react';

const COLORS = {
  cheap: '#10b981',    // Emerald
  medium: '#3b82f6',   // Blue
  frontier: '#8b5cf6', // Purple
};

function StatCard({ title, value, icon: Icon, subtitle, badge, accent = 'indigo' }) {
  const accentColors = {
    indigo: 'bg-indigo-50 text-indigo-600 border-indigo-100',
    emerald: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    violet: 'bg-violet-50 text-violet-600 border-violet-100',
    blue: 'bg-blue-50 text-blue-600 border-blue-100',
  };

  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-sm transition-all flex flex-col justify-between space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{title}</span>
        <div className={`p-2.5 rounded-xl border ${accentColors[accent] || accentColors.indigo}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div>
        <h3 className="text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight">{value}</h3>
        <div className="flex items-center justify-between mt-1">
          {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
          {badge && (
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              {badge}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function TierBadge({ tier }) {
  const lower = (tier || '').toLowerCase();
  if (lower === 'cheap') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
        <Zap className="w-3 h-3" />
        <span>Cheap</span>
      </span>
    );
  }
  if (lower === 'medium') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
        <Shield className="w-3 h-3" />
        <span>Medium</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
      <Sparkles className="w-3 h-3" />
      <span>Frontier</span>
    </span>
  );
}

function formatTimestamp(raw) {
  if (!raw) return '—';
  const ms = raw > 1e11 ? raw : raw * 1000;
  const d = new Date(ms);
  return isNaN(d.getTime()) ? '—' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function Dashboard({ onNavigateToPlayground }) {
  const [summary, setSummary] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchMetrics = useCallback(async (manual = false) => {
    if (manual) setIsRefreshing(true);
    try {
      const [sumRes, recRes] = await Promise.all([
        getMetricsSummary(),
        getRecentMetrics(50),
      ]);
      setSummary(sumRes);
      setRecent(recRes);
      setError(null);
    } catch (e) {
      console.error('Error fetching metrics', e);
      setError(
        e.response?.data?.detail ||
        e.message ||
        'Impossible de contacter la passerelle LLM-Router'
      );
    } finally {
      setLoading(false);
      if (manual) setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(() => fetchMetrics(false), 8000);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  // Loading state
  if (loading && !summary && !error) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-slate-500 space-y-4">
        <div className="relative">
          <div className="w-12 h-12 rounded-full border-2 border-indigo-200 border-t-indigo-600 animate-spin" />
          <Database className="w-5 h-5 text-indigo-600 absolute inset-0 m-auto" />
        </div>
        <p className="text-sm font-medium animate-pulse">Chargement des métriques du routeur...</p>
      </div>
    );
  }

  // Error state (API unreachable)
  if (error && !summary) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[420px] p-6">
        <div className="max-w-lg w-full bg-white rounded-2xl border border-rose-200/80 p-8 shadow-sm text-center space-y-5">
          <div className="w-14 h-14 bg-rose-50 text-rose-600 rounded-2xl flex items-center justify-center mx-auto border border-rose-100 shadow-inner">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <div className="space-y-2">
            <h3 className="text-xl font-bold text-slate-900 tracking-tight">Passerelle LLM-Router Injoignable</h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              Impossible de contacter le serveur backend API (<code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded text-rose-600 font-mono">http://localhost:8000</code>).
            </p>
          </div>
          <div className="bg-slate-50 rounded-xl p-4 text-xs font-mono text-slate-700 text-left border border-slate-200/60 space-y-1">
            <div className="flex items-center text-slate-400 space-x-1 mb-1 font-sans font-semibold">
              <Terminal className="w-3.5 h-3.5" />
              <span>Démarrer le serveur backend :</span>
            </div>
            <p className="text-indigo-600 select-all font-semibold">$ uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload</p>
          </div>
          <button
            onClick={() => fetchMetrics(true)}
            className="inline-flex items-center space-x-2 px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium rounded-xl transition-all shadow-sm active:scale-95 cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Réessayer la connexion</span>
          </button>
        </div>
      </div>
    );
  }

  // Empty SQLite Database state
  const isDbEmpty = !summary || summary.total_requests === 0;

  if (isDbEmpty) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[440px] p-6">
        <div className="max-w-xl w-full bg-white rounded-2xl border border-slate-200/80 p-10 shadow-sm text-center space-y-6">
          <div className="w-16 h-16 bg-gradient-to-tr from-indigo-50 to-blue-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto border border-indigo-100 shadow-inner">
            <Layers className="w-8 h-8" />
          </div>
          <div className="space-y-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Base SQLite Initialisée
            </span>
            <h3 className="text-2xl font-bold text-slate-900 tracking-tight">Aucune métrique enregistrée</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto leading-relaxed">
              Aucune donnée — fais ta première requête dans le Playground pour observer le routage dynamique et le calcul d'économies en direct.
            </p>
          </div>
          <div className="pt-2">
            <button
              onClick={onNavigateToPlayground}
              className="inline-flex items-center space-x-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl shadow-md hover:shadow-indigo-500/20 transition-all active:scale-95 text-sm cursor-pointer"
            >
              <span>Ouvrir le Playground</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Prepare Pie Chart data safely
  const tierDistribution = summary.tier_distribution || {
    cheap: summary.cheap_requests || 0,
    medium: summary.medium_requests || 0,
    frontier: summary.frontier_requests || 0,
  };

  const pieData = Object.entries(tierDistribution)
    .filter(([, value]) => value > 0)
    .map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      tierKey: name.toLowerCase(),
      value,
    }));

  const totalSaved = summary.total_cost_saved ?? 0;
  const avgLatency = summary.avg_latency_ms ?? summary.average_latency_ms ?? 0;
  const savingsPct = summary.savings_percentage ?? 0;

  return (
    <div className="space-y-6 h-full overflow-y-auto pb-10 pr-1">
      {/* Header bar with refresh */}
      <div className="flex items-center justify-between bg-white px-5 py-3.5 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <h2 className="text-base font-bold text-slate-900">Indicateurs de Performance & Économies</h2>
          <p className="text-xs text-slate-500">Mise à jour automatique des métriques SQLite toutes les 8s</p>
        </div>
        <button
          onClick={() => fetchMetrics(true)}
          disabled={isRefreshing}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs font-medium text-slate-700 transition-colors active:scale-95 disabled:opacity-50 cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-indigo-600' : ''}`} />
          <span>Actualiser</span>
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Requêtes Totales"
          value={summary.total_requests.toLocaleString()}
          icon={Hash}
          subtitle={`${summary.total_tokens?.toLocaleString() || 0} tokens routés`}
          accent="indigo"
        />
        <StatCard
          title="Économies Estimées"
          value={`$${totalSaved.toFixed(4)}`}
          icon={DollarSign}
          subtitle="vs coût 100% Frontier"
          badge={`-${savingsPct}%`}
          accent="emerald"
        />
        <StatCard
          title="Latence Moyenne"
          value={`${Math.round(avgLatency)} ms`}
          icon={Clock}
          subtitle="Temps de réponse de bout en bout"
          accent="blue"
        />
        <StatCard
          title="Répartition Économique"
          value={`${summary.cheap_percentage || 0}%`}
          icon={Activity}
          subtitle="Requêtes traitées en tier Cheap"
          accent="violet"
        />
      </div>

      {/* Main Grid: Tier Distribution & Recent Requests */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tier Distribution Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs col-span-1 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Répartition par Tier</h3>
              <span className="text-xs text-slate-400 font-medium">{summary.total_requests} req.</span>
            </div>

            <div className="h-56 relative flex items-center justify-center">
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={80}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={COLORS[entry.tierKey] || '#94a3b8'}
                          stroke="#ffffff"
                          strokeWidth={2}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(val, name) => [`${val} requête(s)`, name]}
                      contentStyle={{
                        borderRadius: '0.75rem',
                        border: '1px solid #e2e8f0',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                        fontSize: '0.75rem',
                      }}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: '0.75rem', paddingTop: '10px' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-xs text-slate-400">Aucune donnée de distribution</div>
              )}
            </div>
          </div>

          {/* Tier summary pills */}
          <div className="grid grid-cols-3 gap-2 pt-4 border-t border-slate-100 text-center">
            <div className="p-2 rounded-xl bg-emerald-50/60 border border-emerald-100">
              <span className="text-[10px] font-bold text-emerald-700 uppercase">Cheap</span>
              <p className="text-sm font-extrabold text-emerald-900">{tierDistribution.cheap || 0}</p>
            </div>
            <div className="p-2 rounded-xl bg-blue-50/60 border border-blue-100">
              <span className="text-[10px] font-bold text-blue-700 uppercase">Medium</span>
              <p className="text-sm font-extrabold text-blue-900">{tierDistribution.medium || 0}</p>
            </div>
            <div className="p-2 rounded-xl bg-purple-50/60 border border-purple-100">
              <span className="text-[10px] font-bold text-purple-700 uppercase">Frontier</span>
              <p className="text-sm font-extrabold text-purple-900">{tierDistribution.frontier || 0}</p>
            </div>
          </div>
        </div>

        {/* Recent Routing Logs Table */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs col-span-1 lg:col-span-2 overflow-hidden flex flex-col">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Journal des Routages Récents</h3>
              <p className="text-xs text-slate-400">Dernières requêtes acheminées par le moteur de routage</p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
              {recent.length} logs
            </span>
          </div>

          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[11px] text-slate-400 uppercase bg-slate-50/80 border-b border-slate-100 font-semibold tracking-wider">
                <tr>
                  <th className="px-5 py-3">Heure</th>
                  <th className="px-5 py-3">Tier</th>
                  <th className="px-5 py-3">Modèle Exécuté</th>
                  <th className="px-5 py-3">Prompt</th>
                  <th className="px-5 py-3 text-right">Latence</th>
                  <th className="px-5 py-3 text-right">Économisé</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recent.length > 0 ? (
                  recent.map((log) => {
                    const modelName = log.actual_model || log.model_used || 'Modèle inconnu';
                    const savedUsd = log.cost_saved_usd ?? log.cost_saved ?? 0;
                    const latency = Math.round(log.latency_ms || 0);

                    return (
                      <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-5 py-3.5 whitespace-nowrap font-mono text-slate-500">
                          {formatTimestamp(log.timestamp)}
                        </td>
                        <td className="px-5 py-3.5 whitespace-nowrap">
                          <TierBadge tier={log.routed_tier} />
                        </td>
                        <td className="px-5 py-3.5 whitespace-nowrap font-mono font-medium text-slate-900">
                          {modelName}
                        </td>
                        <td className="px-5 py-3.5 max-w-[180px] truncate text-slate-600" title={log.prompt_preview}>
                          {log.prompt_preview || '—'}
                        </td>
                        <td className="px-5 py-3.5 whitespace-nowrap text-right font-mono">
                          <span className={latency < 150 ? 'text-emerald-600 font-medium' : latency < 500 ? 'text-blue-600' : 'text-amber-600'}>
                            {latency} ms
                          </span>
                        </td>
                        <td className="px-5 py-3.5 whitespace-nowrap text-right font-mono font-semibold">
                          {savedUsd > 0 ? (
                            <span className="text-emerald-600">
                              +${Number(savedUsd).toFixed(4)}
                            </span>
                          ) : (
                            <span className="text-slate-400">$0.0000</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="6" className="px-6 py-12 text-center text-slate-400">
                      Aucune requête enregistrée récemment.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
