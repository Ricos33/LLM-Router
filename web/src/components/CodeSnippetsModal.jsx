import { useState } from 'react';

export default function CodeSnippetsModal({ onClose, model = 'router-auto', prompt = 'Explain quantum computing in simple terms' }) {
  const [activeTab, setActiveTab] = useState('curl');
  const [copied, setCopied] = useState(false);

  const apiBase = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const cleanPrompt = (prompt || 'Hello, world!').replace(/"/g, '\\"').replace(/\n/g, ' ');

  const snippets = {
    curl: `# Direct Chat Completion (Transparent Routing)
curl -X POST ${apiBase}/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "${model}",
    "messages": [
      {"role": "user", "content": "${cleanPrompt.slice(0, 120)}"}
    ]
  }'

# Response includes diagnostic routing headers:
# X-Router-Tier: cheap | medium | frontier
# X-Router-Model: actual_model_used
# X-Router-Saved-USD: cost_saved_vs_frontier`,

    python: `from openai import OpenAI

# Drop-in replacement for OpenAI SDK
client = OpenAI(
    base_url="${apiBase}/v1",
    api_key="sk-router-local",  # Dummy key; actual provider keys handled by gateway
)

response = client.chat.completions.create(
    model="${model}",  # "router-auto", "router-cheap", or specific model
    messages=[
        {"role": "user", "content": "${cleanPrompt.slice(0, 120)}"}
    ],
)

print(f"Content: {response.choices[0].message.content}")
# Check routed model:
print(f"Model used: {response.model}")`,

    typescript: `import OpenAI from 'openai';

// Initialize with LLM-Router base URL
const openai = new OpenAI({
  baseURL: '${apiBase}/v1',
  apiKey: 'sk-router-local', // Gateway handles upstream credentials
});

async function main() {
  const completion = await openai.chat.completions.create({
    model: '${model}',
    messages: [
      { role: 'user', content: '${cleanPrompt.slice(0, 120)}' }
    ],
  });

  console.log(completion.choices[0].message.content);
}

main();`,

    classify: `# Dedicated Classification & Fit Endpoint
curl -X POST ${apiBase}/v1/classify/explain \\
  -H "Content-Type: application/json" \\
  -d '{
    "messages": [
      {"role": "user", "content": "${cleanPrompt.slice(0, 120)}"}
    ],
    "budget": "Any",
    "providers": ["anthropic", "openai", "google", "mistral"]
  }'

# Returns complexity score, top 10 recommended models,
# dynamic benchmark category weights, and planned fallback chain.`
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(snippets[activeTab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200 border border-gray-200">
        <div className="flex justify-between items-center px-6 py-4 border-b border-gray-100 flex-shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg">🔌</span>
              <h2 className="text-[16px] font-bold text-gray-900">API Integration Snippets</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-gray-100 text-gray-700">
                {model}
              </span>
            </div>
            <p className="text-[12px] text-gray-500 mt-0.5">Use LLM-Router as an OpenAI-compatible drop-in gateway</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black transition-colors p-1">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>

        {/* Language Tabs */}
        <div className="flex border-b border-gray-100 px-6 bg-gray-50/70 text-[12px] font-semibold gap-2 pt-2">
          {[
            { id: 'curl', label: 'cURL' },
            { id: 'python', label: 'Python (OpenAI SDK)' },
            { id: 'typescript', label: 'TypeScript / Node' },
            { id: 'classify', label: 'Classify & Explain' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3.5 py-2 border-b-2 font-medium transition-all ${
                activeTab === tab.id
                  ? 'border-black text-black bg-white rounded-t-lg shadow-2xs'
                  : 'border-transparent text-gray-500 hover:text-black'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Code Content */}
        <div className="p-6 flex-1 overflow-y-auto bg-gray-900 text-gray-100 font-mono text-[12px] relative flex flex-col justify-between">
          <pre className="overflow-x-auto leading-relaxed whitespace-pre-wrap">
            {snippets[activeTab]}
          </pre>
          <div className="mt-4 pt-3 border-t border-gray-800 flex justify-between items-center text-[11px] text-gray-400 font-sans">
            <span>Gateway URL: <code className="text-emerald-400 font-mono">{apiBase}</code></span>
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 bg-white text-black font-semibold rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-1.5 shadow-sm"
            >
              {copied ? '✓ Copied' : 'Copy Snippet'}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 flex justify-between items-center text-[12px] text-gray-500">
          <span>Compatible with OpenAI SDK, LangChain, LiteLLM, Vercel AI SDK.</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-black text-white rounded-lg text-xs font-semibold hover:bg-gray-800 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
