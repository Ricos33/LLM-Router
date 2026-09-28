import { useState, useEffect } from 'react';
import { getMetricsSummary, getRecentMetrics } from '../api/client';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Activity, DollarSign, Clock, Hash } from 'lucide-react';

const COLORS = {
  cheap: '#22c55e',
  medium: '#3b82f6',
  frontier: '#a855f7',
};

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const [sumRes, recRes] = await Promise.all([
          getMetricsSummary(),
          getRecentMetrics(),
        ]);
        setSummary(sumRes);
        setRecent(recRes);
      } catch (e) {
        console.error('Error fetching metrics', e);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !summary) {
    return <div className="flex items-center justify-center h-full text-gray-500">Loading metrics...</div>;
  }

  if (!summary) {
    return <div className="text-red-500 p-4">Failed to load metrics.</div>;
  }

  const pieData = Object.entries(summary.tier_distribution).map(([name, value]) => ({
    name, value
  }));

  const StatCard = ({ title, value, icon: Icon, subtitle }) => (
    <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex items-start space-x-4">
      <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <h3 className="text-2xl font-bold text-gray-900 mt-1">{value}</h3>
        {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
      </div>
    </div>
  );

  return (
    <div className="space-y-6 h-full overflow-y-auto pb-8">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
          title="Total Requests" 
          value={summary.total_requests.toLocaleString()} 
          icon={Hash} 
        />
        <StatCard 
          title="Estimated Savings" 
          value={`$${summary.total_cost_saved.toFixed(4)}`} 
          icon={DollarSign} 
          subtitle="vs all frontier"
        />
        <StatCard 
          title="Avg Latency" 
          value={`${Math.round(summary.average_latency_ms)}ms`} 
          icon={Clock} 
        />
        <StatCard 
          title="Error Rate" 
          value={`${((summary.total_errors / Math.max(1, summary.total_requests)) * 100).toFixed(1)}%`} 
          icon={Activity} 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm col-span-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Tier Distribution</h3>
          <div className="h-64">
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[entry.name.toLowerCase()] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">No data yet</div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 shadow-sm col-span-1 lg:col-span-2 overflow-hidden flex flex-col">
          <div className="p-6 border-b border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900">Recent Routing Logs</h3>
          </div>
          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-gray-500 bg-gray-50 uppercase">
                <tr>
                  <th className="px-6 py-3">Timestamp</th>
                  <th className="px-6 py-3">Tier</th>
                  <th className="px-6 py-3">Model</th>
                  <th className="px-6 py-3">Latency</th>
                  <th className="px-6 py-3">Saved</th>
                </tr>
              </thead>
              <tbody>
                {recent.length > 0 ? recent.map((log) => (
                  <tr key={log.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize ${
                        log.routed_tier === 'cheap' ? 'bg-green-100 text-green-700' :
                        log.routed_tier === 'medium' ? 'bg-blue-100 text-blue-700' :
                        'bg-purple-100 text-purple-700'
                      }`}>
                        {log.routed_tier}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-medium text-gray-900">
                      {log.actual_model}
                    </td>
                    <td className="px-6 py-4 text-gray-500">
                      {Math.round(log.latency_ms)}ms
                    </td>
                    <td className="px-6 py-4 text-green-600 font-medium">
                      ${log.cost_saved_usd.toFixed(4)}
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="5" className="px-6 py-8 text-center text-gray-400">
                      No recent logs found.
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
