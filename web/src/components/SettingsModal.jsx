import { useState, useEffect } from 'react';

export default function SettingsModal({ onClose }) {
  const [keys, setKeys] = useState({ openai: '', anthropic: '', google: '', groq: '', openrouter: '' });
  
  useEffect(() => {
    const saved = localStorage.getItem('provider_keys');
    if (saved) {
      try { setKeys(JSON.parse(saved)); } catch (e) {}
    }
  }, []);

  const handleSave = () => {
    localStorage.setItem('provider_keys', JSON.stringify(keys));
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex justify-between items-center px-5 py-4 border-b border-gray-100">
          <h2 className="text-[15px] font-semibold">API Keys Configuration</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-black">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <div className="p-5 flex flex-col gap-4 text-[13px]">
          <p className="text-gray-500 mb-2">Configure your own API keys to run models directly from the browser. Keys are stored safely in your browser's local storage.</p>
          
          {['openai', 'anthropic', 'google', 'groq', 'openrouter'].map(provider => (
            <div key={provider} className="flex flex-col gap-1.5">
              <label className="font-medium text-gray-700 uppercase text-[10px] tracking-wider">{provider}</label>
              <input 
                type="password"
                placeholder={`sk-...`}
                value={keys[provider] || ''}
                onChange={e => setKeys({...keys, [provider]: e.target.value})}
                className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono text-[12px]"
              />
            </div>
          ))}
        </div>
        
        <div className="px-5 py-4 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-[13px] font-medium text-gray-600 hover:text-black">Cancel</button>
          <button onClick={handleSave} className="px-4 py-2 bg-black text-white text-[13px] font-medium rounded-lg shadow-sm hover:bg-gray-800 transition-colors">Save Keys</button>
        </div>
      </div>
    </div>
  );
}
