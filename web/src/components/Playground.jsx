import { useState, useEffect, useRef } from 'react';
import { useDebounce } from '../hooks/useDebounce';
import { classifyPrompt, chatCompletion, getTierModels } from '../api/client';
import {
  Send,
  Zap,
  Shield,
  Sparkles,
  Bot,
  User,
  RotateCcw,
  Info,
  ChevronRight,
  Sliders,
  Sparkle,
} from 'lucide-react';


const DEFAULT_TIER_MODELS = {
  cheap: {
    tier: 'cheap',
    model: 'gemini-3.8-flash-low',
    provider: 'agy',
    displayName: 'Cheap Tier',
    description: 'Requêtes factuelles, salutations, traductions directes & faible latence',
  },
  medium: {
    tier: 'medium',
    model: 'gemini-3.1-pro-high',
    provider: 'agy',
    displayName: 'Medium Tier',
    description: 'Tâches structurées, snippets de code, résumés détaillés',
  },
  frontier: {
    tier: 'frontier',
    model: 'claude-opus-4-6-thinking',
    provider: 'agy',
    displayName: 'Frontier Tier',
    description: 'Raisonnement profond, architecture système, preuves & code critique',
  },
};

const PROMPT_SUGGESTIONS = [
  {
    tier: 'cheap',
    icon: Zap,
    title: 'Requête Simple (Cheap)',
    prompt: 'Quelle est la capitale du Maroc et sa devise monétaire officielle ?',
  },
  {
    tier: 'medium',
    icon: Shield,
    title: 'Code Intermédiaire (Medium)',
    prompt: 'Écris une fonction Python pour dédupliquer une liste de dictionnaires selon une clé spécifique.',
  },
  {
    tier: 'frontier',
    icon: Sparkles,
    title: 'Raisonnement Avancé (Frontier)',
    prompt: "Conçois l'architecture distribuée d'un algorithme de consensus Raft et démontre la gestion des split-brains.",
  },
];

export default function Playground() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [tierModels, setTierModels] = useState(DEFAULT_TIER_MODELS);
  const [classification, setClassification] = useState(null);
  const [isClassifying, setIsClassifying] = useState(false);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const debouncedInput = useDebounce(input, 300);

  // Auto-scroll chat to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  // Load backend tier model mapping on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await getTierModels();
        if (data && typeof data === 'object' && Object.keys(data).length > 0) {
          setTierModels((prev) => ({ ...prev, ...data }));
        }
      } catch (err) {
        console.warn('Could not fetch backend tier models, using defaults', err);
      }
    };
    fetchModels();
  }, []);

  // Real-time classification on typing (debounced ~300ms)
  useEffect(() => {
    if (!debouncedInput.trim()) {
      setClassification((prev) => (prev ? null : prev));
      return;
    }

    let isSubscribed = true;
    const runClassify = async () => {
      setIsClassifying(true);
      try {
        const context = [...messages, { role: 'user', content: debouncedInput }];
        const res = await classifyPrompt(context);
        if (isSubscribed) {
          setClassification(res);
          if (res.tier_models && Object.keys(res.tier_models).length > 0) {
            setTierModels((prev) => ({ ...prev, ...res.tier_models }));
          }
        }
      } catch (e) {
        console.error('Classification error:', e);
      } finally {
        if (isSubscribed) setIsClassifying(false);
      }
    };

    runClassify();
    return () => {
      isSubscribed = false;
    };
  }, [debouncedInput, messages]);

  const handleSend = async (textToSend) => {
    const content = (textToSend || input).trim();
    if (!content || isSending) return;

    const newMessages = [...messages, { role: 'user', content }];
    setMessages(newMessages);
    setInput('');
    setIsSending(true);

    try {
      const { data, headers } = await chatCompletion(newMessages);
      const assistantMsg = data.choices[0]?.message || {
        role: 'assistant',
        content: 'Réponse vide reçue du modèle.',
      };

      // Extract diagnostic metadata from response headers or body
      const meta = data.router_metadata || {};
      assistantMsg.metadata = {
        tier: headers['x-router-tier'] || meta.routed_tier || 'cheap',
        model: headers['x-router-model'] || meta.actual_model || data.model,
        latency: headers['x-router-latency-ms'] || meta.latency_ms || 0,
        saved: headers['x-router-saved-usd'] || meta.cost_saved_usd || 0,
        provider: meta.upstream_provider || 'llm-router',
      };

      setMessages([...newMessages, assistantMsg]);
    } catch (err) {
      console.error('Error sending message:', err);
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: `Erreur lors de l'exécution du routage : ${err.response?.data?.detail || err.message}`,
          isError: true,
        },
      ]);
    } finally {
      setIsSending(false);
      // Re-classify will be cleared because input is now empty
      setClassification(null);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setClassification(null);
    setInput('');
  };

  // Helper to get active confidence percentages
  const getConfidencePercentages = () => {
    if (classification && classification.probabilities) {
      const { cheap = 0, medium = 0, frontier = 0 } = classification.probabilities;
      return {
        cheap: Math.round(cheap * 100),
        medium: Math.round(medium * 100),
        frontier: Math.round(frontier * 100),
      };
    }
    // Baseline neutral prior before typing
    return {
      cheap: 75,
      medium: 20,
      frontier: 5,
    };
  };

  const confidences = getConfidencePercentages();
  const recommendedTier = classification ? classification.tier : 'cheap';

  const tierStyles = {
    cheap: {
      accent: 'emerald',
      border: 'border-emerald-200',
      activeBorder: 'border-emerald-500 ring-2 ring-emerald-500/20 bg-emerald-50/40',
      barBg: 'bg-emerald-500',
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      textAccent: 'text-emerald-700',
      icon: Zap,
    },
    medium: {
      accent: 'blue',
      border: 'border-blue-200',
      activeBorder: 'border-blue-500 ring-2 ring-blue-500/20 bg-blue-50/40',
      barBg: 'bg-blue-500',
      badge: 'bg-blue-50 text-blue-700 border-blue-200',
      textAccent: 'text-blue-700',
      icon: Shield,
    },
    frontier: {
      accent: 'purple',
      border: 'border-purple-200',
      activeBorder: 'border-purple-500 ring-2 ring-purple-500/20 bg-purple-50/40',
      barBg: 'bg-purple-500',
      badge: 'bg-purple-50 text-purple-700 border-purple-200',
      textAccent: 'text-purple-700',
      icon: Sparkles,
    },
  };

  return (
    <div className="h-full flex flex-col lg:flex-row gap-6 overflow-hidden">
      {/* ============================================================== */}
      {/* LATERAL PANEL (GAUCHE / PANNEAU LATÉRAL) : MODÈLES & JAUGE     */}
      {/* ============================================================== */}
      <div className="w-full lg:w-96 flex flex-col bg-white rounded-2xl border border-slate-200/80 shadow-xs p-5 overflow-y-auto space-y-5 shrink-0">
        {/* Panel Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Routage Prédictif</h3>
              <p className="text-[11px] text-slate-400">Jauge de confiance par modèle</p>
            </div>
          </div>
          <div className="flex items-center space-x-1 px-2 py-1 rounded-full bg-slate-100 text-[10px] font-semibold text-slate-600">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isClassifying ? 'bg-amber-500 animate-ping' : 'bg-emerald-500'
              }`}
            />
            <span>{isClassifying ? 'Évaluation...' : 'Direct (~300ms)'}</span>
          </div>
        </div>

        {/* Model Cards List */}
        <div className="space-y-3.5">
          {['cheap', 'medium', 'frontier'].map((tierKey) => {
            const config = tierModels[tierKey] || DEFAULT_TIER_MODELS[tierKey];
            const isRecommended = recommendedTier === tierKey;
            const pct = confidences[tierKey] || 0;
            const style = tierStyles[tierKey];
            const TierIcon = style.icon;

            return (
              <div
                key={tierKey}
                className={`p-4 rounded-xl border transition-all duration-300 relative ${
                  isRecommended
                    ? `${style.activeBorder} shadow-sm`
                    : 'border-slate-200/70 hover:border-slate-300 bg-white'
                }`}
              >
                {/* Header row: Tier Badge, Model Name & Recommended Tag */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center space-x-2 min-w-0">
                    <div
                      className={`p-1.5 rounded-lg border ${
                        isRecommended ? 'bg-white shadow-xs' : 'bg-slate-50'
                      }`}
                    >
                      <TierIcon
                        className={`w-3.5 h-3.5 ${
                          tierKey === 'cheap'
                            ? 'text-emerald-600'
                            : tierKey === 'medium'
                            ? 'text-blue-600'
                            : 'text-purple-600'
                        }`}
                      />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center space-x-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                          {tierKey}
                        </span>
                        {config.provider && (
                          <span className="text-[9px] font-mono px-1.5 py-0.2 bg-slate-100 text-slate-500 rounded">
                            {config.provider}
                          </span>
                        )}
                      </div>
                      <h4
                        className="text-xs font-mono font-bold text-slate-900 truncate"
                        title={config.model}
                      >
                        {config.model}
                      </h4>
                    </div>
                  </div>

                  {isRecommended && (
                    <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-indigo-600 text-white shadow-xs shrink-0 animate-fade-in">
                      <Sparkle className="w-2.5 h-2.5 fill-white" />
                      <span>Recommandé</span>
                    </span>
                  )}
                </div>

                {/* Animated Progress Bar */}
                <div className="space-y-1.5 mt-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[11px] font-medium text-slate-500">
                      Indice de confiance
                    </span>
                    <span
                      className={`font-mono font-bold text-xs ${
                        isRecommended ? style.textAccent : 'text-slate-700'
                      }`}
                    >
                      {pct}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${style.barBg} rounded-full transition-all duration-300 ease-out`}
                      style={{ width: `${Math.max(2, pct)}%` }}
                    />
                  </div>
                </div>

                {/* Subtitle / Description */}
                <p className="text-[11px] text-slate-500 mt-2.5 leading-snug line-clamp-2">
                  {config.description}
                </p>
              </div>
            );
          })}
        </div>

        {/* Explainability / Reasoning Box */}
        <div className="p-3.5 rounded-xl bg-slate-50/80 border border-slate-200/60 space-y-2">
          <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-700">
            <Info className="w-3.5 h-3.5 text-indigo-500" />
            <span>Explicabilité du Classificateur</span>
          </div>

          {classification ? (
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between text-slate-500">
                <span>Score de complexité :</span>
                <span className="font-mono font-bold text-slate-800">
                  {classification.score != null ? classification.score.toFixed(2) : '—'} / 1.00
                </span>
              </div>
              {classification.reasons?.length > 0 && (
                <div className="space-y-1 pt-1">
                  <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Critères détectés :
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {classification.reasons.map((r, i) => (
                      <span
                        key={i}
                        className="text-[10px] leading-tight px-2 py-1 rounded-md bg-white border border-slate-200 text-slate-700 shadow-2xs"
                      >
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-[11px] text-slate-400 italic leading-relaxed">
              Commencez à taper un prompt dans la zone de chat. L'algorithme évaluera les motifs de code, la syntaxe et la complexité sémantique en direct.
            </p>
          )}
        </div>
      </div>

      {/* ============================================================== */}
      {/* DISCUSSION / CHAT (CENTRE-DROIT) : MESSAGES & TEXTAREA PROMPT   */}
      {/* ============================================================== */}
      <div className="flex-1 flex flex-col bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        {/* Chat Header */}
        <div className="px-6 py-3.5 border-b border-slate-100 flex items-center justify-between bg-white">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-xs">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Passerelle de Chat & Routage</h3>
              <p className="text-[11px] text-slate-400">
                Acheminement automatique vers le modèle optimal via POST /v1/chat/completions
              </p>
            </div>
          </div>

          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Réinitialiser</span>
            </button>
          )}
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center max-w-lg mx-auto py-8 space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-inner">
                <Bot className="w-7 h-7" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                  Testez le routage dynamique
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Tapez votre prompt ci-dessous pour voir la jauge de confiance s'ajuster en temps réel, ou cliquez sur l'un des exemples préconfigurés :
                </p>
              </div>

              {/* Starter Prompt Pills */}
              <div className="grid grid-cols-1 gap-2.5 w-full text-left">
                {PROMPT_SUGGESTIONS.map((item, idx) => {
                  const ItemIcon = item.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSend(item.prompt)}
                      className="p-3.5 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all text-left group flex items-start justify-between gap-3 shadow-2xs"
                    >
                      <div className="flex items-start space-x-3">
                        <div className="p-1.5 rounded-lg bg-slate-100 group-hover:bg-indigo-100 text-slate-600 group-hover:text-indigo-600 transition-colors mt-0.5">
                          <ItemIcon className="w-3.5 h-3.5" />
                        </div>
                        <div>
                          <p className="text-xs font-bold text-slate-800 group-hover:text-indigo-900">
                            {item.title}
                          </p>
                          <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                            "{item.prompt}"
                          </p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-0.5 transition-all mt-1" />
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center shrink-0 shadow-xs mt-1">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 space-y-2 shadow-2xs ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-tr-xs'
                      : 'bg-slate-50 border border-slate-200/80 text-slate-900 rounded-tl-xs'
                  }`}
                >
                  <p className="whitespace-pre-wrap text-xs sm:text-sm leading-relaxed">
                    {msg.content}
                  </p>

                  {/* Diagnostic metadata badge row for Assistant messages */}
                  {msg.metadata && (
                    <div className="pt-2 mt-2 border-t border-slate-200/60 flex flex-wrap items-center gap-2 text-[10px] font-mono text-slate-600">
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-white border border-slate-200 font-sans font-bold capitalize">
                        {msg.metadata.tier === 'cheap' ? (
                          <Zap className="w-2.5 h-2.5 text-emerald-500" />
                        ) : msg.metadata.tier === 'medium' ? (
                          <Shield className="w-2.5 h-2.5 text-blue-500" />
                        ) : (
                          <Sparkles className="w-2.5 h-2.5 text-purple-500" />
                        )}
                        <span>{msg.metadata.tier}</span>
                      </span>

                      <span className="font-semibold text-slate-900 px-1.5 py-0.5 rounded bg-white border border-slate-200">
                        {msg.metadata.model}
                      </span>

                      <span className="text-slate-400">•</span>
                      <span>{Math.round(msg.metadata.latency)} ms</span>

                      {msg.metadata.saved > 0 && (
                        <>
                          <span className="text-slate-400">•</span>
                          <span className="text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 font-semibold font-sans">
                            +${Number(msg.metadata.saved).toFixed(4)} économisé
                          </span>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-xl bg-blue-700 text-white flex items-center justify-center shrink-0 shadow-xs mt-1">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {/* Assistant typing indicator */}
          {isSending && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center shrink-0 shadow-xs">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-slate-50 border border-slate-200/80 rounded-2xl rounded-tl-xs px-4 py-3 flex items-center space-x-2">
                <span className="text-xs text-slate-500 font-medium">Routage en cours</span>
                <div className="flex space-x-1">
                  <div className="w-1.5 h-1.5 bg-indigo-600 rounded-full animate-bounce" />
                  <div className="w-1.5 h-1.5 bg-indigo-600 rounded-full animate-bounce [animation-delay:0.15s]" />
                  <div className="w-1.5 h-1.5 bg-indigo-600 rounded-full animate-bounce [animation-delay:0.3s]" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-slate-50 border-t border-slate-100">
          <div className="relative bg-white rounded-2xl border border-slate-200 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 shadow-xs transition-all">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Posez votre question ou collez du code... Observez la jauge de confiance s'ajuster en direct !"
              className="w-full min-h-[64px] max-h-36 py-3.5 pl-4 pr-14 bg-transparent outline-none resize-none text-xs sm:text-sm text-slate-900 placeholder:text-slate-400"
              rows={2}
            />

            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isSending}
              className="absolute right-2.5 bottom-2.5 p-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl shadow-xs transition-all active:scale-95"
              title="Envoyer la requête (Entrée)"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400 px-2 pt-2">
            <span>
              <strong>Entrée</strong> pour envoyer • <strong>Shift + Entrée</strong> pour retour à la ligne
            </span>
            <span className="hidden sm:inline">Classification heuristique & sémantique sub-second</span>
          </div>
        </div>
      </div>
    </div>
  );
}
