'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { useChatStore } from '@/lib/store';
import { useLanguage } from '@/contexts/LanguageContext';
import { streamChat, analyzeDocument, createSession } from '@/lib/api';
import type { ChatStreamHandlers } from '@/types';
import MessageBubble from './MessageBubble';
import SuggestedQuestions from './SuggestedQuestions';
import FileUploadButton from './FileUploadButton';

// ─── Icons ────────────────────────────────────────────────────────────────────

function SendIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
      <rect x="4" y="4" width="16" height="16" rx="2" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function FileIcon({ isPdf }: { isPdf: boolean }) {
  return isPdf ? (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
  ) : (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ChatInterface() {
  const { t, language } = useLanguage();
  const [token, setToken] = useState<string | undefined>(undefined);

  useEffect(() => {
    setToken(localStorage.getItem('token') ?? undefined);
  }, []);

  const searchParams = useSearchParams();
  const initialQ = searchParams.get('q') ?? '';

  const [input, setInput]               = useState(initialQ);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);

  const textareaRef    = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef       = useRef<AbortController | null>(null);

  const {
    messages, sessionId, isStreaming,
    startUserTurn, startAssistantStream,
    setMessageIntent, setMessageSources, setMessageCitations,
    appendToken, finishStream, setError,
    setSessionId, reset,
  } = useChatStore();

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 192)}px`;
  }, [input]);

  // Scroll to bottom when new content arrives
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const submit = useCallback(
    async (queryText: string, fileOverride?: File | null) => {
      const query = queryText.trim();
      const file  = fileOverride !== undefined ? fileOverride : attachedFile;

      // Must have either text or a file
      if (!query && !file) return;
      if (isStreaming) return;

      setInput('');
      setAttachedFile(null);

      // Display the user turn
      const displayText = file
        ? query || `[📄 ${file.name}]`
        : query;
      startUserTurn(displayText);
      const assistantId = startAssistantStream();

      abortRef.current?.abort();
      abortRef.current = new AbortController();

      try {
        // Ensure session exists
        let sid = sessionId;
        if (!sid) {
          try {
            const s = await createSession(token);
            sid = s.id;
            setSessionId(sid);
          } catch {
            // backend will create one
          }
        }

        const handlers: ChatStreamHandlers = {
          onIntent:    (d)   => setMessageIntent(assistantId, d),
          onSources:   (d)   => setMessageSources(assistantId, d),
          onCitations: (d)   => setMessageCitations(assistantId, d),
          onToken:     (tok) => appendToken(assistantId, tok),
          onDone:      ()    => finishStream(assistantId),
          onError:     (msg) => setError(assistantId, `⚠️ ${msg}`),
        };

        if (file) {
          await analyzeDocument(
            { file, query, sessionId: sid },
            token,
            handlers,
            abortRef.current.signal,
          );
        } else {
          await streamChat(
            { query, sessionId: sid, language },
            token,
            handlers,
            abortRef.current.signal,
          );
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          // User clicked Stop — keep the partial response and reset isStreaming.
          // Without this, isStreaming stays true and the next send (including
          // suggestion card clicks) is silently blocked by the guard above.
          finishStream(assistantId);
        } else if (err instanceof Error) {
          setError(assistantId, `⚠️ ${err.message}`);
        } else {
          setError(assistantId, '⚠️ Unknown error');
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isStreaming, sessionId, token, attachedFile],
  );

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void submit(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void submit(input);
    }
  };

  const handleStop     = ()           => abortRef.current?.abort();
  const handleNewChat  = ()           => { abortRef.current?.abort(); reset(); };
  const handleFileSelect = (f: File)  => setAttachedFile(f);
  const clearFile      = (e: React.MouseEvent) => {
    e.stopPropagation();
    setAttachedFile(null);
  };

  const canSend    = (!!input.trim() || !!attachedFile) && !isStreaming;
  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col h-[100dvh] bg-slate-50">
      {/* ── Header ── */}
      <header className="flex-shrink-0 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-emerald-600 flex items-center justify-center shadow-sm">
            <span className="text-white font-bold text-sm">আ</span>
          </div>
          <div>
            <p className="font-semibold text-slate-800 leading-none">AI Lawyer</p>
            <p className="text-xs text-slate-400 mt-0.5">বাংলাদেশের আইন, আপনার ভাষায়</p>
          </div>
        </div>

        {hasMessages && (
          <button
            onClick={handleNewChat}
            className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors"
          >
            <PlusIcon />
            {t('chat.newChat')}
          </button>
        )}
      </header>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {!hasMessages ? (
          initialQ ? (
            <div className="flex flex-col items-center justify-center h-full gap-4 px-4 text-center">
              <div className="w-14 h-14 rounded-2xl bg-emerald-600 flex items-center justify-center shadow-md">
                <span className="text-white font-bold text-2xl">আ</span>
              </div>
              <div className="max-w-md">
                <p className="text-sm text-slate-500 mb-3">এই প্রশ্নটি পাঠাতে নিচের বোতামে ক্লিক করুন:</p>
                <p className="text-slate-800 font-medium bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm shadow-sm mb-4">
                  {initialQ}
                </p>
                <button
                  onClick={() => void submit(initialQ)}
                  className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-colors shadow-sm"
                >
                  প্রশ্ন পাঠান →
                </button>
              </div>
            </div>
          ) : (
            <SuggestedQuestions onSelect={(q) => void submit(q)} />
          )
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        ) }
      </div>

      {/* ── Input ── */}
      <div className="flex-shrink-0 border-t border-slate-200 bg-white px-4 py-4">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleFormSubmit}>

            {/* File attachment preview chip */}
            {attachedFile && (
              <div className="mb-2 flex items-center gap-1.5 animate-fade-in">
                <div className="inline-flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium px-3 py-1.5 rounded-full max-w-xs">
                  <FileIcon isPdf={attachedFile.type === 'application/pdf'} />
                  <span className="truncate max-w-[180px]">{attachedFile.name}</span>
                  <span className="text-emerald-500 ml-0.5">
                    ({(attachedFile.size / 1024).toFixed(0)} KB)
                  </span>
                  <button
                    type="button"
                    onClick={clearFile}
                    className="ml-1 text-emerald-500 hover:text-emerald-700 transition-colors"
                    aria-label="Remove attachment"
                  >
                    <XIcon />
                  </button>
                </div>
              </div>
            )}

            <div className="flex gap-2 items-end">
              {/* Upload button */}
              <FileUploadButton
                onFileSelect={handleFileSelect}
                disabled={isStreaming}
              />

              {/* Text input */}
              <div className="flex-1">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    attachedFile
                      ? 'দলিল সম্পর্কে প্রশ্ন করুন…'
                      : t('chat.placeholder')
                  }
                  rows={1}
                  disabled={isStreaming}
                  className="w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:opacity-60 transition-all leading-relaxed"
                />
              </div>

              {/* Send / Stop button */}
              {isStreaming ? (
                <button
                  type="button"
                  onClick={handleStop}
                  className="flex-shrink-0 w-11 h-11 rounded-2xl bg-slate-200 hover:bg-slate-300 text-slate-600 flex items-center justify-center transition-colors"
                  title="বন্ধ করুন"
                >
                  <StopIcon />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!canSend}
                  className="flex-shrink-0 w-11 h-11 rounded-2xl bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-200 disabled:text-slate-400 text-white flex items-center justify-center transition-colors shadow-sm"
                  title="পাঠান"
                >
                  <SendIcon />
                </button>
              )}
            </div>

            <p className="text-xs text-slate-400 mt-2 text-center">
              Enter পাঠাতে · Shift+Enter নতুন লাইন · 📎 ছবি বা PDF সংযুক্ত করুন
            </p>
          </form>

          <p className="text-[11px] text-slate-400 text-center mt-3 leading-relaxed">
            ⚠️ এটি AI-সহায়তা, আইনি পরামর্শ নয়। গুরুত্বপূর্ণ বিষয়ে একজন যোগ্য আইনজীবীর সাথে পরামর্শ করুন।
          </p>
        </div>
      </div>
    </div>
  );
}
