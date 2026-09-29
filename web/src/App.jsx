import { useState, useEffect, useCallback } from 'react';
import Playground from './components/Playground';
import Dashboard from './components/Dashboard';
import Benchmark from './components/Benchmark';
import Catalog from "./components/Catalog";
import ABTesting from "./components/ABTesting"; './components/Catalog';
import SettingsModal from './components/SettingsModal';
import { getModels } from './api/client';

const TABS = [
  { key: 'playground', label: 'Playground' },
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'benchmark', label: 'Benchmark' },
  { key: 'catalog', label: 'Catalog' },
  { key: 'abtest', label: 'A/B Test' },
];

function App() {
  const [activeTab, setActiveTab] = useState('playground');
  const [modelCount, setModelCount] = useState(0);
  const [showSettings, setShowSettings] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [replayPrompt, setReplayPrompt] = useState('');
  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem('jev-theme');
      if (saved === 'dark' || saved === 'light') return saved;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem('jev-theme', theme);
    } catch { /* ignore */ }
  }, [theme]);

  const handleReplayPrompt = useCallback((promptText) => {
    setReplayPrompt(promptText);
    setActiveTab('playground');
  }, []);

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

  // Close mobile menu on tab change
  const handleTabChange = useCallback((key) => {
    setActiveTab(key);
    setMobileMenuOpen(false);
  }, []);

  // Keyboard navigation: arrow keys in tab bar
  const handleTabKeyDown = useCallback((e, currentIdx) => {
    let nextIdx = currentIdx;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      nextIdx = (currentIdx + 1) % TABS.length;
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      nextIdx = (currentIdx - 1 + TABS.length) % TABS.length;
    } else if (e.key === 'Home') {
      e.preventDefault();
      nextIdx = 0;
    } else if (e.key === 'End') {
      e.preventDefault();
      nextIdx = TABS.length - 1;
    }
    if (nextIdx !== currentIdx) {
      handleTabChange(TABS[nextIdx].key);
      // Focus the new tab button
      setTimeout(() => {
        document.querySelector(`[data-tab="${TABS[nextIdx].key}"]`)?.focus();
      }, 0);
    }
  }, [handleTabChange]);

  // Close mobile menu on Escape
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape' && mobileMenuOpen) setMobileMenuOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [mobileMenuOpen]);

  return (
    <div className="flex flex-col h-screen bg-base text-txt-base font-sans">
      <header className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-brd bg-surface shrink-0" role="banner">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 bg-black text-white rounded-md flex items-center justify-center font-bold text-sm" aria-hidden="true">J</div>
          <span className="font-semibold text-[15px]">Jev Router</span>
          <span className="text-txt-muted text-[13px] ml-2 hidden md:inline">Pick the right model. No completion.</span>
        </div>

        {/* Desktop nav */}
        <div className="hidden sm:flex items-center gap-6 text-[13px]">
          <nav role="tablist" aria-label="Main navigation" className="flex gap-5 text-txt-muted">
            {TABS.map((tab, idx) => (
              <button
                key={tab.key}
                role="tab"
                data-tab={tab.key}
                aria-selected={activeTab === tab.key}
                tabIndex={activeTab === tab.key ? 0 : -1}
                onClick={() => handleTabChange(tab.key)}
                onKeyDown={(e) => handleTabKeyDown(e, idx)}
                className={activeTab === tab.key ? 'text-txt-base font-medium' : 'hover:text-txt-base transition-colors'}
              >
                {tab.label}
              </button>
            ))}
          </nav>
          <div className="flex items-center gap-1.5 text-txt-muted font-medium bg-gray-50 px-2.5 py-1 rounded-md border border-brd" aria-live="polite">
            <span className="w-2 h-2 rounded-full bg-emerald-500" aria-hidden="true"></span>
            {modelCount} models • live
          </div>
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="text-txt-muted hover:text-txt-base transition-colors"
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          >
            {theme === 'dark' ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
            )}
          </button>
          <button
            onClick={() => setShowSettings(true)}
            className="text-txt-muted hover:text-txt-base transition-colors"
            aria-label="Open settings"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>

        {/* Mobile hamburger */}
        <div className="flex sm:hidden items-center gap-3">
          <div className="flex items-center gap-1.5 text-txt-muted text-xs font-medium bg-gray-50 px-2 py-0.5 rounded-md border border-brd" aria-live="polite">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" aria-hidden="true"></span>
            {modelCount}
          </div>
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="text-txt-muted hover:text-txt-base p-1"
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
            )}
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="text-txt-muted hover:text-txt-base p-1"
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
            )}
          </button>
        </div>
      </header>

      {/* Mobile dropdown menu */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-b border-brd bg-surface animate-fade-in">
          <nav role="tablist" aria-label="Mobile navigation" className="flex flex-col">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                role="tab"
                aria-selected={activeTab === tab.key}
                onClick={() => handleTabChange(tab.key)}
                className={`px-4 py-3 text-left text-[14px] border-b border-gray-100 last:border-b-0 transition-colors ${
                  activeTab === tab.key ? 'text-txt-base font-medium bg-gray-50' : 'text-txt-muted hover:text-txt-base hover:bg-gray-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
            <button
              onClick={() => { setShowSettings(true); setMobileMenuOpen(false); }}
              className="px-4 py-3 text-left text-[14px] text-txt-muted hover:text-txt-base hover:bg-gray-50 flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
              Settings
            </button>
          </nav>
        </div>
      )}

      <main className="flex-1 overflow-hidden" role="tabpanel" aria-label={`${activeTab} panel`}>
        {activeTab === 'playground' && <Playground modelsCount={modelCount} initialPrompt={replayPrompt} />}
        {activeTab === 'dashboard' && <Dashboard onReplayPrompt={handleReplayPrompt} />}
        {activeTab === 'benchmark' && <Benchmark />}
        {activeTab === 'catalog' && <Catalog onSelectModel={() => setActiveTab('playground')} />}
      </main>
      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
}

export default App;
