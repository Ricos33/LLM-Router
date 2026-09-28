import { useState } from 'react';
import Playground from './components/Playground';
import Dashboard from './components/Dashboard';
import { LayoutDashboard, MessageSquare, Settings } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('playground');

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-100 flex items-center space-x-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">R</div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">LLM Router</h1>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          <button
            onClick={() => setActiveTab('playground')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-colors ${
              activeTab === 'playground'
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <MessageSquare className="w-5 h-5" />
            <span>Playground</span>
          </button>
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-colors ${
              activeTab === 'dashboard'
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <LayoutDashboard className="w-5 h-5" />
            <span>Dashboard</span>
          </button>
        </nav>
        <div className="p-4 border-t border-gray-100 text-xs text-gray-400 text-center">
          LLM-Router v0.1.0
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden flex flex-col h-full bg-gray-50 p-6">
        <header className="mb-6 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-800">
            {activeTab === 'playground' ? 'Playground' : 'Metrics Dashboard'}
          </h2>
        </header>
        <main className="flex-1 overflow-hidden">
          {activeTab === 'playground' ? <Playground /> : <Dashboard />}
        </main>
      </div>
    </div>
  );
}

export default App;
