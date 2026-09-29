import { useState, useEffect } from 'react';
import { getRules, createRule, deleteRule, resetRules } from '../api/client';

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
  const [activeTab, setActiveTab] = useState('keys'); // 'keys' | 'rules'
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

  useEffect(() => {
    if (activeTab === 'rules') {
      loadRules();
    }
  }, [activeTab]);

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
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-100 flex-shrink-0 flex justify-between items-center">
          <div>
            <h2 className="text-[15px] font-semibold text-gray-900">Settings & Policy Rules</h2>
            <div className="flex gap-4 mt-2">
              <button
                onClick={() => setActiveTab('keys')}
                className={`text-xs font-semibold pb-1 border-b-2 transition-colors ${
                  activeTab === 'keys'
                    ? 'border-black text-black'
                    : 'border-transparent text-gray-400 hover:text-gray-700'
                }`}
              >
                API Keys & Health
              </button>
              <button
                onClick={() => setActiveTab('rules')}
                className={`text-xs font-semibold pb-1 border-b-2 transition-colors flex items-center gap-1.5 ${
                  activeTab === 'rules'
                    ? 'border-black text-black'
                    : 'border-transparent text-gray-400 hover:text-gray-700'
                }`}
              >
                <span>Routing Rules</span>
                <span className="text-[10px] bg-gray-100 px-1.5 py-0.2 rounded-full font-mono">
                  {rules.length || 4}
                </span>
              </button>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black">
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
                      <label className="font-semibold text-gray-700 text-[11px] tracking-wide">{p.name}</label>
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
                          className="text-[9px] text-gray-400 hover:text-red-600 hover:bg-red-50 px-1.5 py-0.5 rounded font-medium transition-colors"
                          title="Simulate upstream failure (trip circuit)"
                        >
                          ⚡ Trip
                        </button>
                      )}
                      {keys[p.id] ? (
                        <span className="text-[10px] text-emerald-600 font-medium bg-emerald-50 px-1.5 py-0.5 rounded">Configured</span>
                      ) : (
                        <span className="text-[10px] text-gray-400">Not set</span>
                      )}
                    </div>
                  </div>
                  <input 
                    type="password"
                    placeholder={p.placeholder}
                    value={keys[p.id] || ''}
                    onChange={e => setKeys({...keys, [p.id]: e.target.value})}
                    className="px-3 py-1.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono text-[11px]"
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
              <span className="text-xs text-gray-500">
                Deterministic regex and keyword overrides evaluated before classification.
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleResetRules}
                  className="text-[11px] text-gray-500 hover:text-black border border-gray-200 px-2 py-1 rounded hover:bg-gray-50"
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
              <form onSubmit={handleCreateRule} className="bg-gray-50 border border-gray-200 rounded-xl p-3.5 flex flex-col gap-2.5 text-xs animate-in fade-in">
                <div className="font-semibold text-gray-800 text-[11px] uppercase tracking-wider">New Routing Rule</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[10px] text-gray-500 mb-0.5">Rule Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Legal & Contracts"
                      required
                      value={newRule.name}
                      onChange={e => setNewRule({ ...newRule, name: e.target.value })}
                      className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-gray-500 mb-0.5">Target Tier</label>
                    <select
                      value={newRule.target_tier}
                      onChange={e => setNewRule({ ...newRule, target_tier: e.target.value })}
                      className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs outline-none capitalize"
                    >
                      <option value="cheap">Cheap</option>
                      <option value="medium">Medium</option>
                      <option value="frontier">Frontier</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] text-gray-500 mb-0.5">Trigger Keywords (comma separated)</label>
                  <input
                    type="text"
                    placeholder="e.g. nda, compliance, indemnification, legal"
                    value={newRule.keywords}
                    onChange={e => setNewRule({ ...newRule, keywords: e.target.value })}
                    className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[10px] text-gray-500 mb-0.5">Target Model (optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. anthropic/claude-opus-5.5"
                      value={newRule.target_model}
                      onChange={e => setNewRule({ ...newRule, target_model: e.target.value })}
                      className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs font-mono outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-gray-500 mb-0.5">Priority (default 100)</label>
                    <input
                      type="number"
                      value={newRule.priority}
                      onChange={e => setNewRule({ ...newRule, priority: e.target.value })}
                      className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs outline-none"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2 mt-1">
                  <button
                    type="button"
                    onClick={() => setShowAddRule(false)}
                    className="px-2.5 py-1 text-gray-500 hover:text-black"
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
              <div className="py-8 text-center text-gray-400">Loading rules...</div>
            ) : (
              <div className="flex flex-col gap-2.5">
                {rules.map(r => (
                  <div key={r.id} className="bg-white border border-gray-200 rounded-lg p-3 shadow-2xs flex flex-col gap-1.5">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-semibold text-gray-900 text-[12px]">{r.name}</div>
                        <div className="text-[10px] font-mono text-gray-400">{r.id}</div>
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
                      <p className="text-[11px] text-gray-500 leading-snug">{r.description}</p>
                    )}
                    {r.target_model && (
                      <div className="text-[10px] text-gray-600">
                        Target model: <span className="font-mono font-medium text-gray-900">{r.target_model}</span>
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
                          <span className="text-[9px] text-gray-400">+{r.keywords.length - 4} more</span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
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
            className="text-[10px] font-medium text-gray-500 hover:text-red-600 bg-white border border-gray-200 hover:border-red-200 hover:bg-red-50 px-2 py-1 rounded shadow-xs transition-colors"
          >
            Clear Semantic Cache
          </button>
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="px-3.5 py-1.5 text-[12px] font-medium text-gray-600 hover:text-black">Cancel</button>
            <button 
              onClick={handleSave} 
              className={`px-4 py-1.5 text-white text-[12px] font-medium rounded-lg shadow-sm transition-all ${
                savedSuccess ? 'bg-emerald-600' : 'bg-black hover:bg-gray-800'
              }`}
            >
              {savedSuccess ? 'Saved!' : 'Save Keys'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
