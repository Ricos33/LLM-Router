import { useState, useEffect } from 'react';
import Playground from './components/Playground';
import Dashboard from './components/Dashboard';
import { getHealth } from './api/client';
import {
  Layers,
  MessageSquare,
  BarChart3,
  ExternalLink,
} from 'lucide-react';


const GithubIcon = ({ className = 'w-3.5 h-3.5' }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
    />
  </svg>
);

function App() {
  const [activeTab, setActiveTab] = useState('playground');
  const [backendHealth, setBackendHealth] = useState({ online: false, data: null });

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await getHealth();
        setBackendHealth({ online: true, data: res });
      } catch {
        setBackendHealth({ online: false, data: null });
      }
    };


    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-[#f8fafc] text-slate-900 font-sans selection:bg-indigo-100 selection:text-indigo-800 overflow-hidden">
      {/* ============================================================== */}
      {/* HERO / HEADER GLOBAL                                           */}
      {/* ============================================================== */}
      <header className="bg-white border-b border-slate-200/80 px-6 py-3.5 shrink-0 z-10 shadow-2xs">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Brand & Project Summary */}
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-blue-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20 shrink-0">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-extrabold tracking-tight text-slate-900">
                  LLM-Router <span className="text-indigo-600">Gateway</span>
                </h1>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                  v0.1.0
                </span>
                {backendHealth.online && (
                  <span className="hidden sm:inline-flex items-center space-x-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span>API Active</span>
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 line-clamp-1">
                Passerelle intelligente OpenAI-compatible • Routage dynamique par complexité & économies de coûts
              </p>
            </div>
          </div>

          {/* Navigation Tabs & External Links */}
          <div className="flex items-center space-x-3 self-end md:self-auto">
            {/* Segmented Control */}
            <div className="flex p-1 bg-slate-100/80 rounded-xl border border-slate-200/60 shadow-inner">
              <button
                onClick={() => setActiveTab('playground')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                  activeTab === 'playground'
                    ? 'bg-white text-indigo-600 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Playground</span>
              </button>

              <button
                onClick={() => setActiveTab('dashboard')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                  activeTab === 'dashboard'
                    ? 'bg-white text-indigo-600 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                <span>Dashboard Métriques</span>
              </button>
            </div>

            {/* GitHub Link */}
            <a
              href="https://github.com/Ricos33/LLM-Router"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-medium text-slate-700 transition-colors shadow-2xs"
            >
              <GithubIcon className="w-3.5 h-3.5" />
              <span>GitHub</span>
              <ExternalLink className="w-2.5 h-2.5 text-slate-400" />
            </a>
          </div>
        </div>
      </header>

      {/* ============================================================== */}
      {/* MAIN CONTENT AREA                                              */}
      {/* ============================================================== */}
      <main className="flex-1 overflow-hidden p-4 sm:p-6 max-w-7xl mx-auto w-full">
        {activeTab === 'playground' ? (
          <Playground />
        ) : (
          <Dashboard onNavigateToPlayground={() => setActiveTab('playground')} />
        )}
      </main>
    </div>
  );
}

export default App;
