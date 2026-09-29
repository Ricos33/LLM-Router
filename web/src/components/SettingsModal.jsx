import { useState, useEffect } from 'react';

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
  const [keys, setKeys] = useState({});
  const [health, setHealth] = useState({});
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('provider_keys');
    if (saved) {
      try { setKeys(JSON.parse(saved)); } catch (e) {}
    }
    const apiBase = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    fetch(`${apiBase}/v1/providers/health`)
      .then(res => res.json())
      .then(setHealth)
      .catch(() => {});
  }, []);

  const handleTrip = async (provider) => {
    const apiBase = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
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
    const apiBase = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
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

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex justify-between items-center px-5 py-4 border-b border-gray-100 flex-shrink-0">
          <div>
            <h2 className="text-[15px] font-semibold text-gray-900">Provider API Keys & Health</h2>
            <p className="text-[11px] text-gray-500 mt-0.5">8 authorized providers with live circuit breaker tracking</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
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
        
        <div className="px-5 py-3.5 border-t border-gray-100 bg-gray-50 flex justify-between items-center flex-shrink-0">
          <span className="text-[11px] text-gray-400">Keys are never sent to third parties</span>
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
