'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessage, CitationSource } from '@/types';
import { cn } from '@/lib/utils';
import IntentBadge from './IntentBadge';

// ─── Collapsible citations ─────────────────────────────────────────────────────

function CitationsSection({ citations }: { citations: CitationSource[] }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors select-none"
      >
        <span>📚 উৎস ({citations.length})</span>
        <span className="text-[10px]">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="mt-2 flex flex-wrap gap-2">
          {citations.map((c, i) => (
            <div
              key={i}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-2 text-xs max-w-[220px]"
            >
              <div className="font-medium text-slate-700 truncate">{c.law_name}</div>
              {c.section && (
                <div className="text-emerald-700 mt-0.5">ধারা {c.section}</div>
              )}
              {c.title && (
                <div className="text-slate-400 italic text-[11px] truncate mt-0.5">{c.title}</div>
              )}
              <div className="text-slate-400 text-[11px] mt-1">
                {Math.round(c.relevance * 100)}% প্রাসঙ্গিক
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── MessageBubble ─────────────────────────────────────────────────────────────

interface Props {
  message: ChatMessage;
}

export default function MessageBubble({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[80%] bg-emerald-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  const isError = Boolean(message.error);

  return (
    <div className="flex justify-start animate-fade-in">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-emerald-100 flex items-center justify-center mr-3 mt-1">
        <span className="text-emerald-700 font-bold text-xs">আ</span>
      </div>

      <div className="flex-1 max-w-[88%] space-y-3">
        {/* Intent badge */}
        {message.intent && !isError && (
          <IntentBadge intent={message.intent} />
        )}

        {/* Message content */}
        <div
          className={cn(
            'rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm',
            isError
              ? 'bg-red-50 border border-red-200 text-red-700'
              : 'bg-white border border-slate-100',
          )}
        >
          {message.content ? (
            <div
              className={cn(
                'prose prose-sm max-w-none',
                message.isStreaming && !message.content.endsWith(' ')
                  ? 'cursor-blink'
                  : '',
              )}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          ) : message.isStreaming ? (
            <div className="flex items-center gap-1.5 py-1">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          ) : null}

          {/* Collapsible citations — shown below message after response completes */}
          {message.citations && message.citations.length > 0 && !isError && !message.isStreaming && (
            <CitationsSection citations={message.citations} />
          )}
        </div>

        {/* Timestamp */}
        {!message.isStreaming && (
          <p className="text-xs text-slate-400 ml-1">
            {message.timestamp.toLocaleTimeString('bn-BD', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        )}
      </div>
    </div>
  );
}
