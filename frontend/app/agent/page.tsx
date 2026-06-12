'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ToolUsed {
  name:   string;
  input:  Record<string, unknown>;
  result: Record<string, unknown>;
}

interface AgentMessage {
  role:       'user' | 'assistant';
  content:    string;
  tools_used?: ToolUsed[];
}

interface AgentResponse {
  response:   string;
  tools_used: ToolUsed[];
  language:   string;
}

// ─── Tool metadata ────────────────────────────────────────────────────────────

const TOOL_META: Record<string, { icon: string; labelBn: string; labelEn: string; color: string }> = {
  search_laws:              { icon: '🔍', labelBn: 'আইন অনুসন্ধান',  labelEn: 'Search Laws',         color: 'bg-blue-100 text-blue-700 border-blue-200'    },
  get_law_details:          { icon: '📖', labelBn: 'আইনের বিবরণ',   labelEn: 'Law Details',          color: 'bg-indigo-100 text-indigo-700 border-indigo-200' },
  search_legal_templates:   { icon: '📝', labelBn: 'টেমপ্লেট খোঁজ', labelEn: 'Find Templates',       color: 'bg-purple-100 text-purple-700 border-purple-200' },
  calculate_legal_deadline: { icon: '📅', labelBn: 'সময়সীমা গণনা',  labelEn: 'Calculate Deadline',   color: 'bg-orange-100 text-orange-700 border-orange-200' },
  get_court_info:           { icon: '🏛️', labelBn: 'আদালত তথ্য',    labelEn: 'Court Info',           color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  check_legal_eligibility:  { icon: '⚖️', labelBn: 'যোগ্যতা যাচাই', labelEn: 'Check Eligibility',    color: 'bg-rose-100 text-rose-700 border-rose-200'    },
};

function toolResultSummary(tool: ToolUsed, lang: string): string {
  const r = tool.result;
  if (tool.name === 'search_laws')              return lang === 'en' ? `${(r.count as number) ?? 0} laws found` : `${(r.count as number) ?? 0}টি আইন পাওয়া গেছে`;
  if (tool.name === 'get_law_details')          return (r.name as string) ?? '';
  if (tool.name === 'search_legal_templates')   return lang === 'en' ? `${(r.count as number) ?? 0} templates` : `${(r.count as number) ?? 0}টি টেমপ্লেট`;
  if (tool.name === 'calculate_legal_deadline') return (r.deadline_date as string) ?? '';
  if (tool.name === 'get_court_info')           return (r.court_name as string) ?? '';
  if (tool.name === 'check_legal_eligibility')  return (r.eligible as boolean) ? (lang === 'en' ? '✓ Eligible' : '✓ যোগ্য') : (lang === 'en' ? '✗ Not eligible' : '✗ যোগ্য নয়');
  return '';
}

// ─── Suggested questions ──────────────────────────────────────────────────────

const SUGGESTIONS_BN = [
  'চেক ডিজঅনারের মামলায় আমার কী করা উচিত?',
  'জমি বিক্রির চুক্তিতে কী কী থাকা দরকার?',
  'শ্রম আদালতে মামলা করতে কত দিন সময় আছে?',
  'জামিনের জন্য কী যোগ্যতা লাগে?',
];

const SUGGESTIONS_EN = [
  'What should I do in a cheque dishonour case?',
  'What should a land sale contract include?',
  'How many days to file a labour court case?',
  'What are the eligibility criteria for bail?',
];

// ─── Capability cards ─────────────────────────────────────────────────────────

interface CapCard { icon: string; titleBn: string; titleEn: string; descBn: string; descEn: string }

const CAPABILITIES: CapCard[] = [
  { icon: '🔍', titleBn: 'আইন অনুসন্ধান',   titleEn: 'Law Search',       descBn: 'প্রাসঙ্গিক আইন ও ধারা স্বয়ংক্রিয়ভাবে খুঁজে দেয়', descEn: 'Automatically finds relevant laws and sections' },
  { icon: '⚖️', titleBn: 'যোগ্যতা যাচাই',   titleEn: 'Eligibility Check', descBn: 'জামিন, আপিল ও আইনি সহায়তার যোগ্যতা পরীক্ষা',       descEn: 'Checks bail, appeal, and legal aid eligibility'  },
  { icon: '📅', titleBn: 'সময়সীমা গণনা',    titleEn: 'Deadline Calc',    descBn: 'আইনি সময়সীমা ও গুরুত্বপূর্ণ তারিখ গণনা করে',       descEn: 'Calculates legal deadlines and important dates'  },
  { icon: '🏛️', titleBn: 'আদালত তথ্য',      titleEn: 'Court Info',       descBn: 'আদালতের এখতিয়ার, ফি ও যোগাযোগ তথ্য',               descEn: 'Court jurisdiction, fees and contact details'    },
];

// ─── Markdown renderer ────────────────────────────────────────────────────────

function renderMarkdown(text: string): string {
  const lines = text.split('\n');
  let inTable = false;
  let tableHtml = '';
  let result = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      if (!inTable) {
        inTable = true;
        tableHtml = '<table style="border-collapse:collapse;width:100%;margin:8px 0">';
      }
      if (line.includes('---')) continue;
      const cells = line.split('|').filter(c => c.trim() !== '');
      const tag = i === 0 || lines[i - 1]?.includes('---') ? 'th' : 'td';
      tableHtml += '<tr>' + cells.map(c =>
        `<${tag} style="border:1px solid #e2e8f0;padding:6px 12px;text-align:left">${c.trim()}</${tag}>`
      ).join('') + '</tr>';
    } else {
      if (inTable) {
        result += tableHtml + '</table>';
        inTable = false;
        tableHtml = '';
      }
      result += line + '\n';
    }
  }
  if (inTable) result += tableHtml + '</table>';

  return result
    .replace(/### (.*?)(\n|$)/g,    '<h3 style="font-size:15px;font-weight:600;margin:12px 0 6px">$1</h3>')
    .replace(/## (.*?)(\n|$)/g,     '<h2 style="font-size:17px;font-weight:600;margin:14px 0 8px">$1</h2>')
    .replace(/\*\*(.*?)\*\*/g,      '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g,          '<em>$1</em>')
    .replace(/^- (.*?)(\n|$)/gm,    '<li style="margin:4px 0">$1</li>')
    .replace(/^(\d+)\. (.*?)(\n|$)/gm, '<li style="margin:4px 0">$2</li>')
    .replace(/---/g,                '<hr style="border:none;border-top:1px solid #e2e8f0;margin:12px 0"/>')
    .replace(/\n/g,                 '<br/>');
}

// ─── Tool badge ───────────────────────────────────────────────────────────────

function ToolBadge({ tool, lang, expanded, onToggle }: {
  tool:     ToolUsed;
  lang:     string;
  expanded: boolean;
  onToggle: () => void;
}) {
  const meta = TOOL_META[tool.name] ?? { icon: '🔧', labelBn: tool.name, labelEn: tool.name, color: 'bg-slate-100 text-slate-600 border-slate-200' };
  const summary = toolResultSummary(tool, lang);
  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={onToggle}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-medium transition-all ${meta.color} hover:opacity-80`}
      >
        <span>{meta.icon}</span>
        <span>{lang === 'en' ? meta.labelEn : meta.labelBn}</span>
        {summary && <span className="opacity-60">→ {summary}</span>}
        <span className="opacity-50">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <div className="mt-2 p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-600 font-mono text-xs overflow-x-auto">
          <div className="mb-1 font-semibold text-slate-400 uppercase tracking-wide text-[10px]">Input</div>
          <pre className="whitespace-pre-wrap break-all">{JSON.stringify(tool.input, null, 2)}</pre>
          <div className="mt-2 mb-1 font-semibold text-slate-400 uppercase tracking-wide text-[10px]">Result</div>
          <pre className="whitespace-pre-wrap break-all">{JSON.stringify(tool.result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function MessageBubble({ msg, lang }: { msg: AgentMessage; lang: string }) {
  const [expandedTools, setExpandedTools] = useState<Record<number, boolean>>({});
  const isUser = msg.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} gap-3`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0 mt-1">
          🤖
        </div>
      )}
      <div className={`max-w-[85%] ${isUser ? 'max-w-[75%]' : ''}`}>
        {/* Tool badges */}
        {!isUser && msg.tools_used && msg.tools_used.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {msg.tools_used.map((tool, i) => (
              <ToolBadge
                key={i}
                tool={tool}
                lang={lang}
                expanded={!!expandedTools[i]}
                onToggle={() => setExpandedTools((prev) => ({ ...prev, [i]: !prev[i] }))}
              />
            ))}
          </div>
        )}
        {/* Bubble */}
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? 'bg-purple-600 text-white rounded-br-sm'
              : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm prose prose-sm max-w-none'
          }`}
        >
          {isUser ? (
            msg.content
          ) : (
            <div
              dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
            />
          )}
        </div>
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 text-sm flex-shrink-0 mt-1">
          👤
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AgentPage() {
  const { t, language } = useLanguage();

  const [messages,    setMessages]    = useState<AgentMessage[]>([]);
  const [input,       setInput]       = useState('');
  const [isThinking,  setIsThinking]  = useState(false);
  const [error,       setError]       = useState<string | null>(null);
  const [history,     setHistory]     = useState<Array<{ role: string; content: string }>>([]);

  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const suggestions = language === 'en' ? SUGGESTIONS_EN : SUGGESTIONS_BN;

  async function sendMessage(text: string) {
    if (!text.trim() || isThinking) return;
    setError(null);

    const userMsg: AgentMessage = { role: 'user', content: text.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);

    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
      const res = await fetch(`${API_URL}/api/agent/chat`, {
        method:  'POST',
        headers,
        body: JSON.stringify({
          message:              text.trim(),
          language,
          conversation_history: history,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null) as Record<string, unknown> | null;
        const detail = body && typeof body.detail === 'string' ? body.detail : `HTTP ${res.status}`;
        throw new Error(detail);
      }

      const data = await res.json() as AgentResponse;
      const assistantMsg: AgentMessage = {
        role:       'assistant',
        content:    data.response,
        tools_used: data.tools_used,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setHistory((prev) => [
        ...prev,
        { role: 'user', content: text.trim() },
        { role: 'assistant', content: data.response },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'সার্ভারের সাথে সংযোগ স্থাপন করা যায়নি।');
    } finally {
      setIsThinking(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void sendMessage(input);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void sendMessage(input);
    }
  }

  function handleNewChat() {
    setMessages([]);
    setHistory([]);
    setInput('');
    setError(null);
    inputRef.current?.focus();
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <NavBar />

      {/* Hero */}
      <section
        style={{ background: 'linear-gradient(135deg, #3b0764 0%, #4c1d95 50%, #5b21b6 100%)' }}
        className="py-12 px-4"
      >
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-purple-400/20 border border-purple-400/40 text-purple-200 text-sm font-medium px-4 py-1.5 rounded-full mb-4">
            ⚡ Powered by Claude AI Tools
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3">
            {t('agent.title')}
          </h1>
          <p className="text-purple-200 text-base max-w-xl mx-auto leading-relaxed">
            {t('agent.subtitle')}
          </p>
        </div>

        {/* Capability cards */}
        <div className="max-w-4xl mx-auto mt-8 grid grid-cols-2 sm:grid-cols-4 gap-3 px-0">
          {CAPABILITIES.map((cap) => (
            <div key={cap.titleEn} className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl p-3 text-center">
              <div className="text-2xl mb-1">{cap.icon}</div>
              <div className="text-white font-semibold text-xs mb-0.5">
                {language === 'en' ? cap.titleEn : cap.titleBn}
              </div>
              <div className="text-purple-200 text-[11px] leading-tight">
                {language === 'en' ? cap.descEn : cap.descBn}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Chat area */}
      <div className="flex-1 max-w-3xl w-full mx-auto px-4 py-6 flex flex-col gap-4">

        {/* New chat button */}
        {messages.length > 0 && (
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleNewChat}
              className="text-xs font-medium text-purple-600 hover:text-purple-800 border border-purple-200 hover:border-purple-400 px-3 py-1.5 rounded-lg transition-colors"
            >
              + {language === 'en' ? 'New Chat' : 'নতুন চ্যাট'}
            </button>
          </div>
        )}

        {/* Suggested questions (only before any messages) */}
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
              {language === 'en' ? 'Suggested questions' : 'প্রস্তাবিত প্রশ্ন'}
            </p>
            <div className="grid sm:grid-cols-2 gap-2">
              {suggestions.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => void sendMessage(q)}
                  className="text-left px-4 py-3 bg-white border border-slate-200 rounded-xl text-sm text-slate-700 hover:border-purple-300 hover:bg-purple-50 transition-colors shadow-sm"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <MessageBubble key={i} msg={msg} lang={language} />
          ))}

          {/* Thinking indicator */}
          {isThinking && (
            <div className="flex justify-start gap-3">
              <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white text-sm flex-shrink-0 mt-1">
                🤖
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <div className="flex items-center gap-2 text-sm text-purple-600">
                  <span className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                  {t('agent.thinking')}
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
              ⚠️ {error}
            </div>
          )}
        </div>

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="sticky bottom-0 bg-white/95 backdrop-blur-md border-t border-slate-200 px-4 py-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('agent.placeholder')}
            rows={1}
            className="flex-1 resize-none bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent placeholder:text-slate-400 transition-all"
            style={{ minHeight: '44px', maxHeight: '120px' }}
            disabled={isThinking}
          />
          <button
            type="submit"
            disabled={isThinking || !input.trim()}
            className="flex-shrink-0 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-300 text-white font-semibold px-5 py-3 rounded-xl text-sm transition-colors shadow-sm"
          >
            {isThinking ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
            ) : (
              language === 'en' ? 'Send' : 'পাঠান'
            )}
          </button>
        </form>
        <p className="max-w-3xl mx-auto mt-2 text-[11px] text-slate-400 text-center">
          {language === 'en'
            ? '⚠️ AI assistance only — not legal advice. Consult a qualified lawyer for serious matters.'
            : '⚠️ এটি AI সহায়তা — আইনি পরামর্শ নয়। গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর পরামর্শ নিন।'}
        </p>
      </div>
    </div>
  );
}
