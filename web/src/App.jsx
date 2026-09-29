import { useState, useEffect } from 'react';
import Playground from './components/Playground';
import Dashboard from './components/Dashboard';
import { getModels } from './api/client';

function App() {
  const [activeTab, setActiveTab] = useState('playground');
  const [modelCount, setModelCount] = useState(0);

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
          </div>
          <div className="flex items-center gap-1.5 text-gray-500 font-medium bg-gray-50 px-2.5 py-1 rounded-md border border-gray-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            {modelCount} models • live
          </div>
        </div>
      </header>
      <main className="flex-1 overflow-hidden">
        {activeTab === 'playground' ? <Playground modelsCount={modelCount} /> : <Dashboard />}
      </main>
    </div>
  );
}

export default App;
