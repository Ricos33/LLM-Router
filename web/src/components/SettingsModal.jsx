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
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('provider_keys');
    if (saved) {
      try { setKeys(JSON.parse(saved)); } catch (e) {}
    }
  }, []);

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
            <h2 className="text-[15px] font-semibold text-gray-900">Provider API Keys</h2>
            <p className="text-[11px] text-gray-500 mt-0.5">8 authorized providers — stored locally in browser</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <div className="p-5 flex flex-col gap-3.5 text-[13px] overflow-y-auto">
          {AUTHORIZED_PROVIDERS.map(p => (
            <div key={p.id} className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-gray-700 text-[11px] tracking-wide">{p.name}</label>
                {keys[p.id] ? (
                  <span className="text-[10px] text-emerald-600 font-medium bg-emerald-50 px-1.5 py-0.5 rounded">Configured</span>
                ) : (
                  <span className="text-[10px] text-gray-400">Not set</span>
                )}
              </div>
              <input 
                type="password"
                placeholder={p.placeholder}
                value={keys[p.id] || ''}
                onChange={e => setKeys({...keys, [p.id]: e.target.value})}
                className="px-3 py-1.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono text-[11px]"
              />
            </div>
          ))}
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
