import { useState, useEffect } from 'react';
import {
  getRules,
  createRule,
  deleteRule,
  resetRules,
  getBudgetStatus,
  testBudgetAlert,
  configureBudget,
  clearBudgetAlerts,
} from '../api/client';

const AUTHORIZED_PROVIDERS = [
  { id: 'openai', name: 'OpenAI (GPT)', placeholder: 'sk-proj-...' },
  { id: 'anthropic', name: 'Anthropic (Claude)', placeholder: 'sk-ant-...' },
  { id: 'google', name: 'Google (Gemini)', placeholder: 'AIzaSy...' },
  { id: 'qwen', name: 'Qwen (Alibaba)', placeholder: 'sk-...' },
  { id: 'mistral', name: 'Mistral AI', placeholder: '...' },
  { id: 'deepseek', name: 'DeepSeek', placeholder: 'sk-...' },
  { id: 'meta', name: 'Meta (Llama)', placeholder: '...' },
  { id: 'xai', name: 'xAI (Grok)', placeholder: 'xai-...' },
];

export default function SettingsModal({ onClose }) {
  const [activeTab, setActiveTab] = useState('keys'); // 'keys' | 'rules' | 'budget'
  const [keys, setKeys] = useState({});
  const [health, setHealth] = useState({});
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Routing Rules state
  const [rules, setRules] = useState([]);
  const [rulesLoading, setRulesLoading] = useState(false);
  const [showAddRule, setShowAddRule] = useState(false);
  const [newRule, setNewRule] = useState({
    id: '',
    name: '',
    keywords: '',
    target_tier: 'medium',
    target_model: '',
    priority: 100,
  });

  // Enterprise Budget State
  const [budgetStatus, setBudgetStatus] = useState(null);
  const [budgetForm, setBudgetForm] = useState({ monthly_budget_usd: '', webhook_url: '', thresholds: '50, 80, 90, 100' });
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [budgetMessage, setBudgetMessage] = useState(null);

  const apiBase = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    const saved = localStorage.getItem('provider_keys');
    if (saved) {
      try { setKeys(JSON.parse(saved)); } catch (e) {}
    }
    fetch(`${apiBase}/v1/providers/health`)
      .then(res => res.json())
      .then(setHealth)
      .catch(() => {});
  }, [apiBase]);

  const loadRules = async () => {
    setRulesLoading(true);
    try {
      const data = await getRules();
      setRules(data);
    } catch (e) {
      console.warn('Failed to load rules', e);
    } finally {
      setRulesLoading(false);
    }
  };

  const loadBudget = async () => {
    try {
      const data = await getBudgetStatus();
      setBudgetStatus(data);
      if (data) {
        setBudgetForm({
          monthly_budget_usd: data.monthly_budget_usd !== undefined ? (data.monthly_budget_usd || '') : '',
          webhook_url: data.webhook_url || '',
          thresholds: (data.thresholds || [50, 80, 90, 100]).join(', '),
        });
      }
    } catch (e) {
      console.warn('Failed to load budget status', e);
    }
  };

  useEffect(() => {
    if (activeTab === 'rules') {
      loadRules();
    } else if (activeTab === 'budget') {
      loadBudget();
    }
  }, [activeTab]);

  const handleSaveBudget = async (e) => {
    if (e) e.preventDefault();
    setBudgetLoading(true);
    try {
      const threshArr = budgetForm.thresholds
        ? budgetForm.thresholds.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n))
        : [50, 80, 90, 100];
      await configureBudget({
        monthly_budget_usd: budgetForm.monthly_budget_usd === '' ? 0.0 : parseFloat(budgetForm.monthly_budget_usd),
        webhook_url: budgetForm.webhook_url,
        thresholds: threshArr,
      });
      await loadBudget();
      setSavedSuccess(true);
      setBudgetMessage('Budget configuration saved successfully.');
      setTimeout(() => {
        setSavedSuccess(false);
        setBudgetMessage(null);
      }, 4000);
    } catch (err) {
      setBudgetMessage('Failed to save budget: ' + (err.message || err));
    } finally {
      setBudgetLoading(false);
    }
  };

  const handleTriggerTest = async () => {
    setBudgetLoading(true);
    try {
      const res = await testBudgetAlert();
      setBudgetMessage(
        res.webhook_tested
          ? (res.webhook_dispatched ? 'Synthetic alert dispatched to webhook!' : 'Test alert created (webhook returned HTTP error).')
          : 'Synthetic alert recorded in local history.'
      );
      await loadBudget();
      setTimeout(() => setBudgetMessage(null), 5000);
    } catch (err) {
      setBudgetMessage('Failed test alert: ' + (err.message || err));
    } finally {
      setBudgetLoading(false);
    }
  };

  const handleClearAlertHistory = async () => {
    try {
      await clearBudgetAlerts();
      await loadBudget();
      setBudgetMessage('Alert history cleared.');
      setTimeout(() => setBudgetMessage(null), 3000);
    } catch (err) {
      console.warn(err);
    }
  };

  const handleTrip = async (provider) => {
    try {
      const res = await fetch(`${apiBase}/v1/chaos/trip`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, reason: `Settings simulated outage on ${provider}` }),
      });
      if (res.ok) {
        const data = await res.json();
        setHealth(data.all_health);
      }
    } catch (e) {
      console.warn(e);
    }
  };

  const handleReset = async (provider = 'all') => {
    try {
      const res = await fetch(`${apiBase}/v1/chaos/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      });
      if (res.ok) {
        const data = await res.json();
        setHealth(data.all_health);
      }
    } catch (e) {
      console.warn(e);
    }
  };

  const handleSave = () => {
    localStorage.setItem('provider_keys', JSON.stringify(keys));
    setSavedSuccess(true);
    setTimeout(() => {
      onClose();
    }, 400);
  };

  const handleCreateRule = async (e) => {
    e.preventDefault();
    if (!newRule.name.trim()) return;
    const ruleId = newRule.id.trim() || newRule.name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    const keywordsList = newRule.keywords
      .split(',')
      .map(k => k.trim())
      .filter(Boolean);

    try {
      await createRule({
        id: ruleId,
        name: newRule.name.trim(),
        keywords: keywordsList,
        target_tier: newRule.target_tier,
        target_model: newRule.target_model.trim() || null,
        priority: parseInt(newRule.priority) || 100,
        enabled: true,
      });
      setShowAddRule(false);
      setNewRule({ id: '', name: '', keywords: '', target_tier: 'medium', target_model: '', priority: 100 });
      loadRules();
    } catch (err) {
      alert('Failed to create rule: ' + err.message);
    }
  };

  const handleDeleteRule = async (ruleId) => {
    if (!confirm(`Delete rule "${ruleId}"?`)) return;
    try {
      await deleteRule(ruleId);
      loadRules();
    } catch (err) {
      alert('Failed to delete rule: ' + err.message);
    }
  };

  const handleResetRules = async () => {
    if (!confirm('Reset routing rules to system defaults?')) return;
    try {
      await resetRules();
      loadRules();
    } catch (err) {
      alert('Failed to reset rules: ' + err.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-surface rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-100 flex-shrink-0 flex justify-between items-center">
          <div>
            <h2 className="text-[15px] font-semibold text-txt-base">Settings & Policy Rules</h2>
            <div className="flex gap-4 mt-2">
              <button
                onClick={() => setActiveTab('keys')}
                className={`text-xs font-semibold pb-1 border-b-2 transition-colors ${
                  activeTab === 'keys'
                    ? 'border-black text-txt-base'
                    : 'border-transparent text-txt-muted hover:text-txt-base'
                }`}
              >
                API Keys & Health
              </button>
              <button
                onClick={() => setActiveTab('rules')}
                className={`text-xs font-semibold pb-1 border-b-2 transition-colors flex items-center gap-1.5 ${
                  activeTab === 'rules'
                    ? 'border-black text-txt-base'
                    : 'border-transparent text-txt-muted hover:text-txt-base'
                }`}
              >
                <span>Routing Rules</span>
                <span className="text-[10px] bg-gray-100 px-1.5 py-0.2 rounded-full font-mono">
                  {rules.length || 4}
                </span>
              </button>
              <button
                onClick={() => setActiveTab('budget')}
                className={`text-xs font-semibold pb-1 border-b-2 transition-colors flex items-center gap-1.5 ${
                  activeTab === 'budget'
                    ? 'border-black text-txt-base'
                    : 'border-transparent text-txt-muted hover:text-txt-base'
                }`}
              >
                <span>Budget & Webhooks</span>
                {budgetStatus?.status && budgetStatus.status !== 'unlimited' && (
                  <span className={`text-[9px] px-1.5 py-0.2 rounded-full font-mono font-bold ${
                    budgetStatus.status === 'critical' ? 'bg-red-100 text-red-700' :
                    budgetStatus.status === 'warning' ? 'bg-amber-100 text-amber-700' :
                    'bg-emerald-100 text-emerald-700'
                  }`}>
                    {budgetStatus.percent_used?.toFixed(0)}%
                  </span>
                )}
              </button>
            </div>
          </div>
          <button onClick={onClose} className="text-txt-muted hover:text-txt-base">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        {/* Tab 1: API Keys & Health */}
        {activeTab === 'keys' && (
          <div className="p-5 flex flex-col gap-3.5 text-[13px] overflow-y-auto">
            {AUTHORIZED_PROVIDERS.map(p => {
              const pHealth = health[p.id]?.status || 'healthy';
              const isTripped = pHealth === 'tripped';
              return (
                <div key={p.id} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span 
                        className={`w-2 h-2 rounded-full ${isTripped ? 'bg-red-500 animate-pulse' : 'bg-emerald-500'}`} 
                        title={isTripped ? 'Circuit tripped (temporarily avoiding)' : 'Circuit healthy'}
                      />
                      <label className="font-semibold text-txt-base text-[11px] tracking-wide">{p.name}</label>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {isTripped ? (
                        <button
                          type="button"
                          onClick={() => handleReset(p.id)}
                          className="text-[9px] text-emerald-700 bg-emerald-100 hover:bg-emerald-200 px-1.5 py-0.5 rounded font-bold transition-colors"
                          title="Restore circuit breaker"
                        >
                          ↺ Restore
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleTrip(p.id)}
                          className="text-[9px] text-txt-muted hover:text-red-600 hover:bg-red-50 px-1.5 py-0.5 rounded font-medium transition-colors"
                          title="Simulate upstream failure (trip circuit)"
                        >
                          ⚡ Trip
                        </button>
                      )}
                      {keys[p.id] ? (
                        <span className="text-[10px] text-emerald-600 font-medium bg-emerald-50 px-1.5 py-0.5 rounded">Configured</span>
                      ) : (
                        <span className="text-[10px] text-txt-muted">Not set</span>
                      )}
                    </div>
                  </div>
                  <input 
                    type="password"
                    placeholder={p.placeholder}
                    value={keys[p.id] || ''}
                    onChange={e => setKeys({...keys, [p.id]: e.target.value})}
                    className="px-3 py-1.5 border border-brd rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono text-[11px]"
                  />
                </div>
              );
            })}
          </div>
        )}

        {/* Tab 2: Routing Rules & Policies */}
        {activeTab === 'rules' && (
          <div className="p-5 flex flex-col gap-4 text-[13px] overflow-y-auto">
            <div className="flex justify-between items-center">
              <span className="text-xs text-txt-muted">
                Deterministic regex and keyword overrides evaluated before classification.
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleResetRules}
                  className="text-[11px] text-txt-muted hover:text-txt-base border border-brd px-2 py-1 rounded hover:bg-gray-50"
                  title="Reset to predefined presets"
                >
                  ↺ Reset
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddRule(!showAddRule)}
                  className="text-[11px] bg-black text-white hover:bg-gray-800 px-2.5 py-1 rounded font-medium"
                >
                  {showAddRule ? 'Close' : '+ Add Rule'}
                </button>
              </div>
            </div>

            {/* Add Custom Rule Form */}
            {showAddRule && (
              <form onSubmit={handleCreateRule} className="bg-gray-50 border border-brd rounded-xl p-3.5 flex flex-col gap-2.5 text-xs animate-in fade-in">
                <div className="font-semibold text-txt-base text-[11px] uppercase tracking-wider">New Routing Rule</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[10px] text-txt-muted mb-0.5">Rule Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Legal & Contracts"
                      required
                      value={newRule.name}
                      onChange={e => setNewRule({ ...newRule, name: e.target.value })}
                      className="w-full px-2 py-1 bg-surface border border-brd rounded text-xs outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-txt-muted mb-0.5">Target Tier</label>
                    <select
                      value={newRule.target_tier}
                      onChange={e => setNewRule({ ...newRule, target_tier: e.target.value })}
                      className="w-full px-2 py-1 bg-surface border border-brd rounded text-xs outline-none capitalize"
                    >
                      <option value="cheap">Cheap</option>
                      <option value="medium">Medium</option>
                      <option value="frontier">Frontier</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] text-txt-muted mb-0.5">Trigger Keywords (comma separated)</label>
                  <input
                    type="text"
                    placeholder="e.g. nda, compliance, indemnification, legal"
                    value={newRule.keywords}
                    onChange={e => setNewRule({ ...newRule, keywords: e.target.value })}
                    className="w-full px-2 py-1 bg-surface border border-brd rounded text-xs outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[10px] text-txt-muted mb-0.5">Target Model (optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. anthropic/claude-opus-5.5"
                      value={newRule.target_model}
                      onChange={e => setNewRule({ ...newRule, target_model: e.target.value })}
                      className="w-full px-2 py-1 bg-surface border border-brd rounded text-xs font-mono outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-txt-muted mb-0.5">Priority (default 100)</label>
                    <input
                      type="number"
                      value={newRule.priority}
                      onChange={e => setNewRule({ ...newRule, priority: e.target.value })}
                      className="w-full px-2 py-1 bg-surface border border-brd rounded text-xs outline-none"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2 mt-1">
                  <button
                    type="button"
                    onClick={() => setShowAddRule(false)}
                    className="px-2.5 py-1 text-txt-muted hover:text-txt-base"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-3 py-1 bg-black text-white rounded font-medium hover:bg-gray-800"
                  >
                    Save Rule
                  </button>
                </div>
              </form>
            )}

            {/* Rules List */}
            {rulesLoading ? (
              <div className="py-8 text-center text-txt-muted">Loading rules...</div>
            ) : (
              <div className="flex flex-col gap-2.5">
                {rules.map(r => (
                  <div key={r.id} className="bg-surface border border-brd rounded-lg p-3 shadow-2xs flex flex-col gap-1.5">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-semibold text-txt-base text-[12px]">{r.name}</div>
                        <div className="text-[10px] font-mono text-txt-muted">{r.id}</div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase tracking-wider ${
                          r.target_tier === 'frontier' ? 'bg-purple-100 text-purple-700' :
                          r.target_tier === 'medium' ? 'bg-blue-100 text-blue-700' :
                          'bg-emerald-100 text-emerald-700'
                        }`}>
                          {r.target_tier}
                        </span>
                        <span className="text-[9px] bg-gray-100 text-gray-600 px-1 py-0.2 rounded font-mono" title="Priority">
                          P:{r.priority}
                        </span>
                        <button
                          onClick={() => handleDeleteRule(r.id)}
                          className="text-gray-300 hover:text-red-600 text-xs ml-1"
                          title="Delete rule"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                    {r.description && (
                      <p className="text-[11px] text-txt-muted leading-snug">{r.description}</p>
                    )}
                    {r.target_model && (
                      <div className="text-[10px] text-gray-600">
                        Target model: <span className="font-mono font-medium text-txt-base">{r.target_model}</span>
                      </div>
                    )}
                    {r.keywords?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {r.keywords.slice(0, 4).map(kw => (
                          <span key={kw} className="bg-gray-100 text-gray-600 text-[9px] px-1.5 py-0.2 rounded">
                            {kw}
                          </span>
                        ))}
                        {r.keywords.length > 4 && (
                          <span className="text-[9px] text-txt-muted">+{r.keywords.length - 4} more</span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Enterprise Budget & Webhooks */}
        {activeTab === 'budget' && (
          <div className="p-5 flex flex-col gap-4 text-[13px] overflow-y-auto">
            {budgetMessage && (
              <div className="text-xs p-2.5 bg-gray-50 border border-brd rounded-lg text-txt-base flex items-center justify-between animate-in fade-in">
                <span>{budgetMessage}</span>
                <button onClick={() => setBudgetMessage(null)} className="text-txt-muted hover:text-txt-base">✕</button>
              </div>
            )}

            {/* Current Budget Status Card */}
            <div className="p-3.5 bg-gray-50 rounded-xl border border-brd flex flex-col gap-2">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-txt-base">Budget Status</span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                  budgetStatus?.status === 'critical' ? 'bg-red-100 text-red-700' :
                  budgetStatus?.status === 'warning' ? 'bg-amber-100 text-amber-700' :
                  budgetStatus?.status === 'caution' ? 'bg-blue-100 text-blue-700' :
                  budgetStatus?.status === 'normal' ? 'bg-emerald-100 text-emerald-700' :
                  'bg-gray-200 text-txt-base'
                }`}>
                  {budgetStatus?.status || 'unlimited'}
                </span>
              </div>
              <div className="flex justify-between items-end text-xs font-mono">
                <span className="text-txt-muted">Current Month Spend:</span>
                <span className="font-bold text-txt-base">${(budgetStatus?.current_cost_usd || 0).toFixed(4)}</span>
              </div>
              {budgetStatus?.monthly_budget_usd > 0 && (
                <div>
                  <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden mt-1">
                    <div
                      className={`h-full rounded-full transition-all ${
                        budgetStatus.percent_used >= 100 ? 'bg-red-500' :
                        budgetStatus.percent_used >= 80 ? 'bg-amber-500' :
                        'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, budgetStatus.percent_used || 0)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-txt-muted mt-1 font-mono">
                    <span>{budgetStatus.percent_used?.toFixed(1)}% used</span>
                    <span>${budgetStatus.remaining_usd?.toFixed(2)} remaining</span>
                  </div>
                </div>
              )}
            </div>

            {/* Configuration Form */}
            <form onSubmit={handleSaveBudget} className="flex flex-col gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-txt-base uppercase tracking-wider mb-1">
                  Monthly Budget Limit (USD)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00 (unlimited)"
                  value={budgetForm.monthly_budget_usd}
                  onChange={e => setBudgetForm({ ...budgetForm, monthly_budget_usd: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-surface border border-brd rounded-lg outline-none focus:border-black font-mono"
                />
                <span className="text-[10px] text-txt-muted mt-0.5 block">Set to 0 or leave empty for unlimited routing.</span>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-txt-base uppercase tracking-wider mb-1">
                  Alert Webhook URL
                </label>
                <input
                  type="url"
                  placeholder="https://hooks.slack.com/services/..."
                  value={budgetForm.webhook_url}
                  onChange={e => setBudgetForm({ ...budgetForm, webhook_url: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-surface border border-brd rounded-lg outline-none focus:border-black font-mono"
                />
                <span className="text-[10px] text-txt-muted mt-0.5 block">Payload sent via HTTP POST with threshold details.</span>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-txt-base uppercase tracking-wider mb-1">
                  Alert Thresholds (%)
                </label>
                <input
                  type="text"
                  placeholder="50, 80, 90, 100"
                  value={budgetForm.thresholds}
                  onChange={e => setBudgetForm({ ...budgetForm, thresholds: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-surface border border-brd rounded-lg outline-none focus:border-black font-mono"
                />
                <span className="text-[10px] text-txt-muted mt-0.5 block">Comma-separated percentages to trigger alerts when crossed.</span>
              </div>

              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={handleTriggerTest}
                  disabled={budgetLoading}
                  className="text-xs px-2.5 py-1.5 bg-gray-100 hover:bg-gray-200 text-txt-base rounded-lg font-medium transition-colors flex items-center gap-1 shadow-2xs"
                >
                  ⚡ Send Test Alert
                </button>
                <button
                  type="submit"
                  disabled={budgetLoading}
                  className="text-xs px-4 py-1.5 bg-black hover:bg-gray-800 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  Save Budget Config
                </button>
              </div>
            </form>

            {/* Alert Event History */}
            {budgetStatus?.recent_alerts && budgetStatus.recent_alerts.length > 0 && (
              <div className="pt-3 border-t border-gray-100 flex flex-col gap-2">
                <div className="flex justify-between items-center">
                  <span className="text-[11px] font-semibold text-txt-muted uppercase tracking-wider">
                    Recent Alerts ({budgetStatus.alert_count})
                  </span>
                  <button
                    onClick={handleClearAlertHistory}
                    className="text-[10px] text-txt-muted hover:text-red-600 transition-colors"
                  >
                    Clear History
                  </button>
                </div>
                <div className="flex flex-col gap-1 max-h-36 overflow-y-auto">
                  {budgetStatus.recent_alerts.map((a, idx) => (
                    <div key={idx} className="p-2 rounded bg-gray-50 border border-gray-100 text-[10px] font-mono flex justify-between items-center">
                      <span className="text-txt-base truncate mr-2">{a.message}</span>
                      <span className="text-txt-muted flex-shrink-0">
                        {new Date(a.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Footer */}
        <div className="px-5 py-3.5 border-t border-gray-100 bg-gray-50 flex justify-between items-center flex-shrink-0">
          <button 
            onClick={async () => {
              await fetch(`${apiBase}/v1/cache/clear`, { method: 'POST' });
              alert('Gateway Semantic Cache Cleared!');
            }}
            className="text-[10px] font-medium text-txt-muted hover:text-red-600 bg-surface border border-brd hover:border-red-200 hover:bg-red-50 px-2 py-1 rounded shadow-xs transition-colors"
          >
            Clear Semantic Cache
          </button>
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="px-3.5 py-1.5 text-[12px] font-medium text-gray-600 hover:text-txt-base">Cancel</button>
            {activeTab === 'keys' && (
              <button 
                onClick={handleSave} 
                className={`px-4 py-1.5 text-white text-[12px] font-medium rounded-lg shadow-sm transition-all ${
                  savedSuccess ? 'bg-emerald-600' : 'bg-black hover:bg-gray-800'
                }`}
              >
                {savedSuccess ? 'Saved!' : 'Save Keys'}
              </button>
            )}
            {activeTab === 'budget' && (
              <button 
                onClick={handleSaveBudget} 
                disabled={budgetLoading}
                className={`px-4 py-1.5 text-white text-[12px] font-medium rounded-lg shadow-sm transition-all ${
                  savedSuccess ? 'bg-emerald-600' : 'bg-black hover:bg-gray-800'
                }`}
              >
                {savedSuccess ? 'Saved!' : 'Save Budget'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
