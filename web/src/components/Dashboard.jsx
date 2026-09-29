import { useState, useEffect } from 'react';
import { getMetricsSummary } from '../api/client';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const COLORS = { cheap: '#10b981', medium: '#3b82f6', frontier: '#8b5cf6' };

export default function Dashboard() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    const fetchMetrics = () => getMetricsSummary().then(setSummary).catch(console.warn);
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 8000);
    return () => clearInterval(interval);
  }, []);

  if (!summary) return <div className="flex items-center justify-center h-full text-gray-400 text-sm">Loading metrics...</div>;

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

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8 overflow-y-auto h-full">
      <h2 className="text-xl font-semibold text-gray-900">Dashboard</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white border border-gray-200 rounded-xl shadow-sm">
          <div className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Total Requests</div>
          <div className="text-3xl font-bold text-gray-900">{summary.total_requests}</div>
        </div>
        <div className="p-5 bg-white border border-gray-200 rounded-xl shadow-sm">
          <div className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Cost Saved</div>
          <div className="text-3xl font-bold text-green-600">${(summary.total_cost_saved || 0).toFixed(4)}</div>
        </div>
        <div className="p-5 bg-white border border-gray-200 rounded-xl shadow-sm">
          <div className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Avg Latency</div>
          <div className="text-3xl font-bold text-gray-900">{(summary.avg_latency_ms || summary.average_latency_ms || 0).toFixed(0)} <span className="text-lg font-medium text-gray-400">ms</span></div>
        </div>
        <div className="p-5 bg-white border border-gray-200 rounded-xl shadow-sm">
          <div className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Cheap Tier</div>
          <div className="text-3xl font-bold text-gray-900">{summary.cheap_percentage || 0}<span className="text-lg font-medium text-gray-400">%</span></div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <h3 className="text-sm font-semibold mb-6">Tier Distribution</h3>
          {pieData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={4} dataKey="value">
                    {pieData.map((e, i) => <Cell key={i} fill={COLORS[e.tierKey] || '#999'} stroke="none" />)}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-sm text-gray-400">No data available</div>
          )}
        </div>
      </div>
    </div>
  );
}
