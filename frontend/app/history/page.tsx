'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const LIMIT   = 20;

// ─── Types ────────────────────────────────────────────────────────────────────

interface ChatHistoryItem {
  id:         string;
  session_id: string;
  title:      string;
  intent:     string | null;
  category:   string | null;
  created_at: string;
  updated_at: string;
  preview:    string | null;
}

interface ChatHistoryMessage {
  role:       string;
  content:    string;
  created_at: string;
}

interface ChatSessionDetail {
  session_id: string;
  title:      string;
  messages:   ChatHistoryMessage[];
}

interface PaginatedHistory {
  items:    ChatHistoryItem[];
  page:     number;
  limit:    number;
  total:    number;
  has_more: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const CATEGORY_CONFIG: Record<string, { label: string; color: string }> = {
  criminal:            { label: 'ফৌজদারি',    color: 'bg-red-100 text-red-700' },
  civil:               { label: 'দেওয়ানি',    color: 'bg-blue-100 text-blue-700' },
  family:              { label: 'পারিবারিক',  color: 'bg-pink-100 text-pink-700' },
  land_property:       { label: 'জমি',         color: 'bg-amber-100 text-amber-700' },
  labor_employment:    { label: 'শ্রম',        color: 'bg-orange-100 text-orange-700' },
  constitutional:      { label: 'সাংবিধানিক', color: 'bg-purple-100 text-purple-700' },
  commercial_business: { label: 'ব্যবসায়িক',  color: 'bg-indigo-100 text-indigo-700' },
  banking_finance:     { label: 'ব্যাংকিং',   color: 'bg-cyan-100 text-cyan-700' },
  tenancy_rent:        { label: 'ভাড়া',       color: 'bg-lime-100 text-lime-700' },
  consumer_rights:     { label: 'ভোক্তা',     color: 'bg-teal-100 text-teal-700' },
  digital_cyber:       { label: 'ডিজিটাল',   color: 'bg-violet-100 text-violet-700' },
  immigration:         { label: 'অভিবাসন',   color: 'bg-sky-100 text-sky-700' },
};

const INTENT_LABEL: Record<string, string> = {
  FIND_LAW:      'আইন খোঁজা',
  FIND_SECTION:  'ধারা খোঁজা',
  FIND_CASE:     'নজির',
  EXPLAIN_RIGHTS:'অধিকার',
  CHECK_PROCESS: 'পদ্ধতি',
  COMPARE_LAWS:  'তুলনা',
  GET_DOCUMENT:  'ডকুমেন্ট',
  GENERAL_INFO:  'সাধারণ তথ্য',
  UNKNOWN:       'অন্যান্য',
};

const ALL_CATEGORIES = Object.entries(CATEGORY_CONFIG).map(([value, cfg]) => ({
  value,
  label: cfg.label,
}));

// ─── Helpers ─────────────────────────────────────────────────────────────────

function relativeTimeBN(isoString: string): string {
  const diffSec = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diffSec < 60)      return 'এইমাত্র';
  if (diffSec < 3600)    return `${Math.floor(diffSec / 60)} মিনিট আগে`;
  if (diffSec < 86400)   return `${Math.floor(diffSec / 3600)} ঘণ্টা আগে`;
  if (diffSec < 604800)  return `${Math.floor(diffSec / 86400)} দিন আগে`;
  if (diffSec < 2592000) return `${Math.floor(diffSec / 604800)} সপ্তাহ আগে`;
  return `${Math.floor(diffSec / 2592000)} মাস আগে`;
}

function getCategoryConfig(category: string | null) {
  if (!category) return null;
  return CATEGORY_CONFIG[category] ?? { label: category, color: 'bg-slate-100 text-slate-600' };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function CategoryBadge({ category }: { category: string | null }) {
  const cfg = getCategoryConfig(category);
  if (!cfg) return null;
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function MessageBubble({ msg }: { msg: ChatHistoryMessage }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white text-xs font-bold mr-2 flex-shrink-0 mt-0.5">
          আ
        </div>
      )}
      <div
        className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? 'bg-emerald-600 text-white rounded-br-none'
            : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none'
        }`}
      >
        {msg.content}
        <p className={`text-xs mt-1.5 ${isUser ? 'text-emerald-200' : 'text-slate-400'}`}>
          {relativeTimeBN(msg.created_at)}
        </p>
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-slate-300 flex items-center justify-center text-slate-600 text-xs font-bold ml-2 flex-shrink-0 mt-0.5">
          আপ
        </div>
      )}
    </div>
  );
}

// ─── Modal ────────────────────────────────────────────────────────────────────

function ConversationModal({
  detail,
  loading,
  onClose,
}: {
  detail:   ChatSessionDetail | null;
  loading:  boolean;
  onClose:  () => void;
}) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="bg-white w-full sm:max-w-2xl sm:rounded-2xl rounded-t-2xl shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 flex-shrink-0">
          <div className="min-w-0">
            <h2 className="font-semibold text-slate-800 truncate text-sm">
              {detail?.title ?? '...'}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {detail ? `${detail.messages.length} টি বার্তা` : ''}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors flex-shrink-0 ml-3"
            aria-label="বন্ধ করুন"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-4 bg-slate-50">
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="w-8 h-8 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : detail && detail.messages.length === 0 ? (
            <p className="text-center text-slate-400 text-sm py-10">
              এই কথোপকথনে কোনো বার্তা নেই।
            </p>
          ) : (
            detail?.messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-4 border-t border-slate-100 flex-shrink-0 gap-3">
          <Link
            href="/chat"
            className="flex-1 text-center text-sm bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-4 py-2.5 rounded-xl transition-colors"
          >
            নতুন প্রশ্ন করুন
          </Link>
          <button
            onClick={onClose}
            className="flex-shrink-0 text-sm text-slate-600 hover:text-slate-900 font-medium px-4 py-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors"
          >
            বন্ধ করুন
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function HistoryPage() {
  const { t } = useLanguage();
  const router = useRouter();

  const [sessions,      setSessions]      = useState<ChatHistoryItem[]>([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState<string | null>(null);
  const [page,          setPage]          = useState(1);
  const [total,         setTotal]         = useState(0);
  const [hasMore,       setHasMore]       = useState(false);
  const [loadingMore,   setLoadingMore]   = useState(false);
  const [searchQuery,   setSearchQuery]   = useState('');
  const [filterCat,     setFilterCat]     = useState('');
  const [modalDetail,   setModalDetail]   = useState<ChatSessionDetail | null>(null);
  const [modalLoading,  setModalLoading]  = useState(false);
  const [deletingId,    setDeletingId]    = useState<string | null>(null);

  const tokenRef = useRef<string>('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.replace('/login?redirect=/history');
      return;
    }
    tokenRef.current = token;
    void loadPage(token, 1, true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  async function loadPage(token: string, pageNum: number, replace: boolean) {
    if (pageNum === 1) setLoading(true);
    else setLoadingMore(true);

    try {
      const res  = await fetch(
        `${API_URL}/api/chat-history?page=${pageNum}&limit=${LIMIT}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        router.replace('/login?redirect=/history');
        return;
      }
      if (!res.ok) { setError('ইতিহাস লোড করা যায়নি।'); return; }

      const data = (await res.json()) as PaginatedHistory;
      setSessions((prev) => (replace ? data.items : [...prev, ...data.items]));
      setTotal(data.total);
      setHasMore(data.has_more);
      setPage(pageNum);
    } catch {
      setError('সার্ভারের সাথে সংযোগ করা যাচ্ছে না।');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }

  async function openSession(sessionId: string) {
    setModalDetail(null);
    setModalLoading(true);
    try {
      const res  = await fetch(`${API_URL}/api/chat-history/${sessionId}`, {
        headers: { Authorization: `Bearer ${tokenRef.current}` },
      });
      if (!res.ok) { setModalLoading(false); return; }
      setModalDetail((await res.json()) as ChatSessionDetail);
    } catch {
      /* silently ignore */
    } finally {
      setModalLoading(false);
    }
  }

  async function deleteSession(sessionId: string) {
    if (!confirm('এই কথোপকথন মুছে দিতে চান?')) return;
    setDeletingId(sessionId);
    try {
      const res = await fetch(`${API_URL}/api/chat-history/${sessionId}`, {
        method:  'DELETE',
        headers: { Authorization: `Bearer ${tokenRef.current}` },
      });
      if (res.ok || res.status === 204) {
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        setTotal((t) => Math.max(0, t - 1));
        if (modalDetail?.session_id === sessionId) setModalDetail(null);
      }
    } finally {
      setDeletingId(null);
    }
  }

  // Client-side filter
  const filtered = sessions.filter((s) => {
    const q   = searchQuery.toLowerCase();
    const hit = !q ||
      s.title.toLowerCase().includes(q) ||
      (s.preview?.toLowerCase().includes(q) ?? false);
    const cat = !filterCat || s.category === filterCat;
    return hit && cat;
  });

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50">
        <NavBar />
        <div className="flex items-center justify-center h-[calc(100vh-65px)]">
          <div className="w-10 h-10 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="min-h-screen bg-slate-50">
        <NavBar />
        <div className="flex flex-col items-center justify-center h-[calc(100vh-65px)] gap-4">
          <p className="text-slate-500 text-sm">{error}</p>
          <Link href="/chat" className="text-emerald-600 text-sm font-medium hover:underline">
            চ্যাটে যান →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* ── Hero ──────────────────────────────────────────────────────────────── */}
      <section
        className="px-4 py-10"
        style={{ background: 'linear-gradient(135deg, #064e3b 0%, #065f46 60%, #047857 100%)' }}
      >
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-white">📜 {t('history.title')}</h1>
          <p className="text-emerald-200 mt-2 text-sm">
            আপনার আগের সব আইনি প্রশ্নের কথোপকথন
          </p>
          <p className="text-emerald-300/70 text-xs mt-1">
            মোট {total} টি কথোপকথন
          </p>
        </div>
      </section>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-5">

        {/* ── Search + Filter ───────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
            <input
              type="text"
              placeholder={t('history.search')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </div>
          <select
            value={filterCat}
            onChange={(e) => setFilterCat(e.target.value)}
            className="sm:w-48 px-3 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">সব বিভাগ</option>
            {ALL_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        {/* ── Session list ──────────────────────────────────────────────────── */}
        {filtered.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">📭</div>
            {sessions.length === 0 ? (
              <>
                <p className="text-slate-500 font-medium mb-1">এখনো কোনো কথোপকথন নেই</p>
                <p className="text-slate-400 text-sm mb-6">
                  AI Lawyer-কে আপনার প্রথম আইনি প্রশ্ন করুন
                </p>
                <Link
                  href="/chat"
                  className="inline-block bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-6 py-3 rounded-xl transition-colors text-sm"
                >
                  প্রথম প্রশ্ন করুন →
                </Link>
              </>
            ) : (
              <>
                <p className="text-slate-500 font-medium">কোনো ফলাফল পাওয়া যায়নি</p>
                <p className="text-slate-400 text-sm mt-1">অনুসন্ধান বা ফিল্টার পরিবর্তন করুন</p>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((session) => (
              <div
                key={session.id}
                className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm hover:border-emerald-300 hover:shadow-md transition-all"
              >
                <div className="flex items-start gap-3">
                  {/* Chat icon */}
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 flex-wrap">
                      <p className="font-semibold text-slate-800 text-sm leading-snug truncate max-w-sm">
                        {session.title}
                      </p>
                      <span className="text-xs text-slate-400 flex-shrink-0">
                        {relativeTimeBN(session.updated_at)}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                      <CategoryBadge category={session.category} />
                      {session.intent && INTENT_LABEL[session.intent] && (
                        <span className="text-xs text-slate-400">
                          {INTENT_LABEL[session.intent]}
                        </span>
                      )}
                    </div>

                    {session.preview && (
                      <p className="text-xs text-slate-500 mt-2 leading-relaxed line-clamp-2">
                        {session.preview}
                        {session.preview.length >= 100 && '...'}
                      </p>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2 mt-3">
                      <button
                        onClick={() => void openSession(session.id)}
                        className="text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition-colors"
                      >
                        {t('history.viewFull')}
                      </button>
                      <button
                        onClick={() => void deleteSession(session.id)}
                        disabled={deletingId === session.id}
                        className="text-xs text-slate-400 hover:text-red-500 hover:bg-red-50 px-2.5 py-1.5 rounded-lg transition-colors disabled:opacity-40"
                        aria-label="মুছুন"
                      >
                        {deletingId === session.id ? '...' : '🗑️'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Load more ─────────────────────────────────────────────────────── */}
        {hasMore && !searchQuery && !filterCat && (
          <div className="text-center pt-2">
            <button
              onClick={() => void loadPage(tokenRef.current, page + 1, false)}
              disabled={loadingMore}
              className="text-sm text-emerald-700 hover:text-emerald-900 font-medium px-5 py-2.5 rounded-xl border border-emerald-200 hover:bg-emerald-50 transition-colors disabled:opacity-50"
            >
              {loadingMore ? 'লোড হচ্ছে...' : 'আরও দেখুন'}
            </button>
          </div>
        )}

      </div>

      {/* ── Conversation modal ─────────────────────────────────────────────── */}
      {(modalDetail !== null || modalLoading) && (
        <ConversationModal
          detail  = {modalDetail}
          loading = {modalLoading}
          onClose = {() => { setModalDetail(null); setModalLoading(false); }}
        />
      )}

      <footer className="border-t py-6 text-center text-sm text-slate-400 mt-4">
        <p>⚠️ হ্যালো এ্যাডভকেট আইনি পরামর্শ নয় — গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর সাথে যোগাযোগ করুন।</p>
      </footer>
    </div>
  );
}
