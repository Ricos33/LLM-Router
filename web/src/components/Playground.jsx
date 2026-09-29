import { useState, useEffect } from 'react';
import { useDebounce } from '../hooks/useDebounce';
import { classifyPrompt, getTierModels, chatCompletion } from '../api/client';

export default function Playground() {
  const [input, setInput] = useState('');
  const [classification, setClassification] = useState(null);
  const [tierModels, setTierModels] = useState({});
  const [completion, setCompletion] = useState(null);
  const [isSending, setIsSending] = useState(false);

  const debouncedInput = useDebounce(input, 300);

  const handleSend = async () => {
    if (!input.trim() || isSending) return;
    setIsSending(true);
    setCompletion(null);
    try {
      const res = await chatCompletion([{ role: 'user', content: input }]);
      const content = res.data?.choices?.[0]?.message?.content || JSON.stringify(res.data);
      setCompletion(content);
    } catch (e) {
      console.error(e);
      setCompletion('Error fetching completion.');
    } finally {
      setIsSending(false);
    }
  };

  useEffect(() => {
    getTierModels().then(data => {
      if (data) setTierModels(data);
    }).catch(console.warn);
  }, []);

  useEffect(() => {
    if (!debouncedInput.trim()) {
      setClassification(null);
      return;
    }

    let isSubscribed = true;
    const runClassify = async () => {
      try {
        const res = await classifyPrompt([{ role: 'user', content: debouncedInput }]);
        if (isSubscribed) {
          setClassification(res);
          if (res.tier_models) setTierModels(prev => ({ ...prev, ...res.tier_models }));
        }
      } catch (e) {
        console.error(e);
      }
    };
    runClassify();
    return () => { isSubscribed = false; };
  }, [debouncedInput]);

  const confidences = classification?.probabilities || { cheap: 0.75, medium: 0.20, frontier: 0.05 };

  return (
    <div className="h-full flex flex-col lg:flex-row p-6 gap-6 overflow-hidden max-w-[1400px] mx-auto">
      {/* LEFT: Prompt Input */}
      <div className="w-full lg:w-[40%] flex flex-col gap-4">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Write a prompt here..."
          className="flex-1 w-full p-4 rounded-xl border border-gray-200 bg-white resize-none outline-none focus:border-gray-400 text-sm shadow-sm"
        />
        {completion && (
          <div className="flex-1 w-full p-4 rounded-xl border border-gray-200 bg-gray-50 overflow-y-auto text-sm shadow-sm whitespace-pre-wrap">
            {completion}
          </div>
        )}
        <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-xs text-gray-400">{input.length} chars</span>
          <div className="flex gap-2">
            <button onClick={() => setInput('')} className="px-4 py-2 text-sm text-gray-500 hover:text-black transition-colors">
              Clear
            </button>
            <button 
              onClick={handleSend}
              disabled={isSending || !input.trim()}
              className="px-4 py-2 bg-black text-white text-sm rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
            >
              {isSending ? 'Sending...' : 'Send →'}
            </button>
          </div>
        </div>
      </div>

      {/* CENTER: Analysis */}
      <div className="w-full lg:w-[30%] flex flex-col bg-white rounded-xl border border-gray-200 p-6 shadow-sm overflow-y-auto">
        {!classification ? (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 text-sm text-center">
            <div className="font-semibold text-gray-500 mb-1">No analysis yet</div>
            <span className="text-xs">Type on the left...</span>
          </div>
        ) : (
          <div className="text-sm space-y-6">
            <div>
              <div className="text-xs text-gray-500 mb-1">Recommended Tier</div>
              <div className="font-semibold text-lg capitalize">{classification.tier}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">Complexity Score</div>
              <div className="font-medium text-lg">{classification.score?.toFixed(2) || '—'} / 1.00</div>
            </div>
            {classification.reasons?.length > 0 && (
              <div>
                <div className="text-xs text-gray-500 mb-2">Decision Reasons</div>
                <ul className="list-disc pl-4 space-y-1.5 text-gray-700 text-xs">
                  {classification.reasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* RIGHT: Models */}
      <div className="w-full lg:w-[30%] flex flex-col bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        <div className="p-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold">Catalog</h3>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {['cheap', 'medium', 'frontier'].map((tierKey) => {
            const config = tierModels[tierKey] || {};
            const pct = Math.round((confidences[tierKey] || 0) * 100);
            return (
              <div key={tierKey} className="space-y-1.5">
                <div className="flex justify-between text-sm items-center">
                  <span className="font-medium">{config.model || tierKey}</span>
                  <span className="text-xs text-gray-400">{config.provider || 'unknown'}</span>
                </div>
                <div className="text-xs text-gray-500 capitalize">{tierKey} tier</div>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full rounded-full transition-all duration-300 bg-black"
                      style={{ width: `${Math.max(2, pct)}%` }} 
                    />
                  </div>
                  <span className="text-xs font-mono w-8 text-right text-gray-500">{pct}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
