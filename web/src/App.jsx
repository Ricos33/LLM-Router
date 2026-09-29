import { useState, useEffect } from 'react';
import Playground from './components/Playground';
import Dashboard from './components/Dashboard';
import { getHealth } from './api/client';

function App() {
  const [activeTab, setActiveTab] = useState('playground');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await getHealth();
      } catch {
        // ignore
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-[#fafafa] text-[#111] font-sans">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-black text-white rounded flex items-center justify-center font-bold text-xs">J</div>
          <span className="font-semibold text-sm">Jev Router</span>
          <span className="text-gray-400 text-sm ml-2 hidden sm:inline">Pick the right model. No completion.</span>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <div className="flex gap-4 text-gray-500">
            <button
              onClick={() => setActiveTab('playground')}
              className={activeTab === 'playground' ? 'text-black font-medium' : 'hover:text-black'}
            >
              Playground
            </button>
            <button
              onClick={() => setActiveTab('dashboard')}
              className={activeTab === 'dashboard' ? 'text-black font-medium' : 'hover:text-black'}
            >
              Dashboard
            </button>
          </div>

        </div>
      </header>
      <main className="flex-1 overflow-hidden">
        {activeTab === 'playground' ? <Playground /> : <Dashboard />}
      </main>
    </div>
  );
}

export default App;
