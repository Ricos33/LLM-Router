import { useState, useEffect } from 'react';
import Playground from './components/Playground';
import Dashboard from './components/Dashboard';
import Benchmark from './components/Benchmark';
import Catalog from './components/Catalog';
import SettingsModal from './components/SettingsModal';
import { getModels } from './api/client';

function App() {
  const [activeTab, setActiveTab] = useState('playground');
  const [modelCount, setModelCount] = useState(0);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await getModels();
        if (data) setModelCount(data.length);
      } catch (e) {
        console.warn(e);
      }
    };
    fetchModels();
  }, []);

  return (
    <div className="flex flex-col h-screen bg-[#fafafa] text-[#111] font-sans">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 bg-black text-white rounded-md flex items-center justify-center font-bold text-sm">J</div>
          <span className="font-semibold text-[15px]">Jev Router</span>
          <span className="text-gray-400 text-[13px] ml-2 hidden sm:inline">Pick the right model. No completion.</span>
        </div>
        <div className="flex items-center gap-6 text-[13px]">
          <div className="flex gap-5 text-gray-500">
            <button
              onClick={() => setActiveTab('playground')}
              className={activeTab === 'playground' ? 'text-black font-medium' : 'hover:text-black transition-colors'}
            >
              Playground
            </button>
            <button
              onClick={() => setActiveTab('dashboard')}
              className={activeTab === 'dashboard' ? 'text-black font-medium' : 'hover:text-black transition-colors'}
            >
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('benchmark')}
              className={activeTab === 'benchmark' ? 'text-black font-medium' : 'hover:text-black transition-colors'}
            >
              Benchmark
            </button>
            <button
              onClick={() => setActiveTab('catalog')}
              className={activeTab === 'catalog' ? 'text-black font-medium' : 'hover:text-black transition-colors'}
            >
              Catalog
            </button>
          </div>
          <div className="flex items-center gap-1.5 text-gray-500 font-medium bg-gray-50 px-2.5 py-1 rounded-md border border-gray-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            {modelCount} models • live
          </div>
          <button onClick={() => setShowSettings(true)} className="text-gray-400 hover:text-black">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
      </header>
      <main className="flex-1 overflow-hidden">
        {activeTab === 'playground' && <Playground modelsCount={modelCount} />}
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'benchmark' && <Benchmark />}
        {activeTab === 'catalog' && <Catalog />}
      </main>
      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
}

export default App;
