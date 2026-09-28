import { useState, useEffect } from 'react';
import { useDebounce } from '../hooks/useDebounce';
import { classifyPrompt, chatCompletion } from '../api/client';
import { Send, Cpu, Bot, Zap, Shield, Sparkles } from 'lucide-react';

export default function Playground() {
  const [input, setInput] = useState('');
  const [suggestion, setSuggestion] = useState(null);
  const [loadingSuggestion, setLoadingSuggestion] = useState(false);
  
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [lastResponseInfo, setLastResponseInfo] = useState(null);

  const debouncedInput = useDebounce(input, 300);

  useEffect(() => {
    if (!debouncedInput.trim()) {
      setSuggestion(null);
      return;
    }

    const fetchSuggestion = async () => {
      setLoadingSuggestion(true);
      try {
        const msgs = [...messages, { role: 'user', content: debouncedInput }];
        const res = await classifyPrompt(msgs);
        setSuggestion(res);
      } catch (e) {
        console.error('Failed to classify', e);
      } finally {
        setLoadingSuggestion(false);
      }
    };

    fetchSuggestion();
  }, [debouncedInput, messages]);

  const handleSend = async () => {
    if (!input.trim() || isSending) return;
    
    const newMessages = [...messages, { role: 'user', content: input }];
    setMessages(newMessages);
    setInput('');
    setIsSending(true);
    setSuggestion(null);
    setLastResponseInfo(null);

    try {
      const { data, headers } = await chatCompletion(newMessages);
      const assistantMsg = data.choices[0].message;
      setMessages([...newMessages, assistantMsg]);
      
      setLastResponseInfo({
        tier: headers['x-router-tier'],
        model: headers['x-router-model'],
        latency: headers['x-router-latency-ms'],
        saved: headers['x-router-saved-usd'],
      });
    } catch (error) {
      console.error(error);
      setMessages([...newMessages, { role: 'assistant', content: 'Error: Failed to fetch response.' }]);
    } finally {
      setIsSending(false);
    }
  };

  const TierIcon = ({ tier }) => {
    if (tier === 'cheap') return <Zap className="w-4 h-4 text-green-500" />;
    if (tier === 'medium') return <Shield className="w-4 h-4 text-blue-500" />;
    if (tier === 'frontier') return <Sparkles className="w-4 h-4 text-purple-500" />;
    return <Cpu className="w-4 h-4" />;
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-2">
            <Bot className="w-12 h-12" />
            <p>Start chatting to see intelligent routing in action.</p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
              msg.role === 'user' 
                ? 'bg-blue-600 text-white rounded-tr-none' 
                : 'bg-gray-100 text-gray-800 rounded-tl-none'
            }`}>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
            </div>
          </div>
        ))}
        {isSending && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 rounded-2xl rounded-tl-none px-4 py-3">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}
        
        {lastResponseInfo && !isSending && (
          <div className="flex justify-start">
             <div className="text-xs text-gray-500 bg-gray-50 border border-gray-100 rounded-lg px-3 py-2 flex items-center space-x-3 mt-1">
               <span className="flex items-center"><TierIcon tier={lastResponseInfo.tier} /> <span className="ml-1 capitalize">{lastResponseInfo.tier}</span></span>
               <span className="text-gray-400">|</span>
               <span>{lastResponseInfo.model}</span>
               <span className="text-gray-400">|</span>
               <span>{lastResponseInfo.latency}ms</span>
               {lastResponseInfo.saved > 0 && (
                 <>
                   <span className="text-gray-400">|</span>
                   <span className="text-green-600 font-medium">Saved ${Number(lastResponseInfo.saved).toFixed(4)}</span>
                 </>
               )}
             </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-gray-50 border-t border-gray-100">
        {suggestion && !isSending && (
          <div className="mb-2 flex items-center space-x-2 animate-fade-in-up">
            <div className="flex items-center space-x-1.5 px-2.5 py-1 bg-white border border-gray-200 rounded-full shadow-sm text-xs font-medium text-gray-600">
              <TierIcon tier={suggestion.tier} />
              <span className="capitalize">{suggestion.tier} Tier</span>
              <span className="text-gray-400">•</span>
              <span className="text-gray-500">{suggestion.suggested_model}</span>
              <span className="text-gray-400">•</span>
              <span className={suggestion.confidence > 0.8 ? 'text-green-600' : 'text-orange-500'}>
                {Math.round(suggestion.confidence * 100)}% conf
              </span>
            </div>
            {suggestion.reasons?.length > 0 && (
              <span className="text-xs text-gray-400 truncate max-w-md">
                {suggestion.reasons[0]}
              </span>
            )}
          </div>
        )}

        <div className="relative flex items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Type your message..."
            className="w-full max-h-32 min-h-[56px] bg-white border border-gray-300 rounded-xl py-3 pl-4 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-none"
            rows={1}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isSending}
            className="absolute right-2 bottom-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
