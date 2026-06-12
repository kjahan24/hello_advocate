'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const AUTO_REFRESH_MS = 30 * 60 * 1000; // 30 minutes

// ─── Types ────────────────────────────────────────────────────────────────────

interface NewsItem {
  id:           string;
  title:        string;
  summary:      string;
  link:         string;
  source:       string;
  published_at: string;
  category:     string;
}

interface NewsResponse {
  news:         NewsItem[];
  cached:       boolean;
  last_updated: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const CATEGORIES = ['সব', 'আদালত', 'হাইকোর্ট', 'সুপ্রিম কোর্ট', 'মামলা', 'রায়', 'জামিন', 'আইন'];
const SOURCES    = ['সব', 'প্রথম আলো', 'বিডি প্রতিদিন', 'যুগান্তর'];

const SOURCE_COLORS: Record<string, string> = {
  'প্রথম আলো':    'bg-red-100 text-red-700',
  'বিডি প্রতিদিন': 'bg-blue-100 text-blue-700',
  'যুগান্তর':      'bg-green-100 text-green-700',
};

const CATEGORY_COLORS: Record<string, string> = {
  'আদালত':         'bg-slate-100 text-slate-700',
  'হাইকোর্ট':      'bg-purple-100 text-purple-700',
  'সুপ্রিম কোর্ট': 'bg-indigo-100 text-indigo-700',
  'মামলা':          'bg-orange-100 text-orange-700',
  'রায়':            'bg-emerald-100 text-emerald-700',
  'জামিন':           'bg-yellow-100 text-yellow-700',
  'আইন':            'bg-teal-100 text-teal-700',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function relativeTimeBN(isoString: string): string {
  const diffSec = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diffSec < 60)      return 'এইমাত্র';
  if (diffSec < 3600)    return `${Math.floor(diffSec / 60)} মিনিট আগে`;
  if (diffSec < 86400)   return `${Math.floor(diffSec / 3600)} ঘণ্টা আগে`;
  if (diffSec < 604800)  return `${Math.floor(diffSec / 86400)} দিন আগে`;
  return `${Math.floor(diffSec / 604800)} সপ্তাহ আগে`;
}

// ─── Skeleton card ────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm animate-pulse">
      <div className="flex items-center gap-2 mb-3">
        <div className="h-5 w-16 bg-slate-200 rounded-full" />
        <div className="h-5 w-14 bg-slate-200 rounded-full" />
      </div>
      <div className="space-y-2 mb-3">
        <div className="h-4 bg-slate-200 rounded w-full" />
        <div className="h-4 bg-slate-200 rounded w-4/5" />
      </div>
      <div className="space-y-1.5 mb-4">
        <div className="h-3 bg-slate-100 rounded w-full" />
        <div className="h-3 bg-slate-100 rounded w-11/12" />
        <div className="h-3 bg-slate-100 rounded w-2/3" />
      </div>
      <div className="h-4 w-24 bg-slate-200 rounded" />
    </div>
  );
}

// ─── News card ────────────────────────────────────────────────────────────────

function NewsCard({ item }: { item: NewsItem }) {
  const { t } = useLanguage();
  const srcColor = SOURCE_COLORS[item.source] ?? 'bg-slate-100 text-slate-600';
  const catColor = CATEGORY_COLORS[item.category] ?? 'bg-slate-100 text-slate-600';

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-lg hover:border-blue-200 transition-all duration-200 hover:scale-[1.01] flex flex-col">
      {/* Meta row */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${srcColor}`}>
          {item.source}
        </span>
        <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${catColor}`}>
          {item.category}
        </span>
        <span className="text-xs text-slate-400 ml-auto flex-shrink-0">
          {relativeTimeBN(item.published_at)}
        </span>
      </div>

      {/* Title */}
      <h3 className="font-bold text-slate-800 text-base leading-snug mb-2 line-clamp-2 flex-1">
        {item.title}
      </h3>

      {/* Summary */}
      {item.summary && (
        <p className="text-slate-500 text-sm leading-relaxed line-clamp-3 mb-4">
          {item.summary}
        </p>
      )}

      {/* Link */}
      {item.link && item.link.startsWith('http') && (
        <a
          href={item.link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-semibold text-blue-600 hover:text-blue-800 transition-colors mt-auto"
        >
          {t('news.readMore')}
        </a>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewsPage() {
  const { t } = useLanguage();
  const [news,           setNews]           = useState<NewsItem[]>([]);
  const [loading,        setLoading]        = useState(true);
  const [error,          setError]          = useState<string | null>(null);
  const [lastUpdated,    setLastUpdated]    = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState('সব');
  const [activeSource,   setActiveSource]   = useState('সব');

  const fetchNews = useCallback(async () => {
    setError(null);
    try {
      const res  = await fetch(`${API_URL}/api/news`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as NewsResponse;
      setNews(data.news);
      setLastUpdated(data.last_updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'সংবাদ লোড হয়নি');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchNews();
    const timer = setInterval(() => { void fetchNews(); }, AUTO_REFRESH_MS);
    return () => clearInterval(timer);
  }, [fetchNews]);

  // Client-side filtering
  const filtered = news.filter((item) => {
    const catOk = activeCategory === 'সব' || item.category === activeCategory;
    const srcOk = activeSource   === 'সব' || item.source   === activeSource;
    return catOk && srcOk;
  });

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="bg-gradient-to-br from-blue-900 to-blue-800 px-4 py-12">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-3xl">📰</span>
            <h1 className="text-3xl sm:text-4xl font-bold text-white">{t('news.title')}</h1>
            {/* Live badge */}
            <span className="flex items-center gap-1.5 bg-white/10 border border-white/20 text-white text-xs font-medium px-3 py-1 rounded-full">
              <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
              {t('news.liveUpdate')}
            </span>
          </div>
          <p className="text-blue-200 text-base max-w-xl">
            {t('news.subtitle')}
          </p>
          {lastUpdated && (
            <p className="text-blue-400 text-xs mt-2">
              সর্বশেষ আপডেট: {relativeTimeBN(lastUpdated)}
            </p>
          )}
        </div>
      </section>

      {/* ── Sticky filter bar ─────────────────────────────────────────── */}
      <div className="sticky top-[65px] z-30 bg-white/95 backdrop-blur-md border-b border-slate-100 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-3 space-y-2">
          {/* Category chips */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
            <span className="text-xs font-semibold text-slate-400 flex-shrink-0">বিভাগ:</span>
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`flex-shrink-0 text-xs font-medium px-3 py-1.5 rounded-full transition-colors ${
                  activeCategory === cat
                    ? 'bg-blue-700 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Source + refresh */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <span className="text-xs font-semibold text-slate-400 flex-shrink-0">সূত্র:</span>
            {SOURCES.map((src) => (
              <button
                key={src}
                onClick={() => setActiveSource(src)}
                className={`flex-shrink-0 text-xs font-medium px-3 py-1.5 rounded-full transition-colors ${
                  activeSource === src
                    ? 'bg-blue-700 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {src}
              </button>
            ))}
            <button
              onClick={() => { setLoading(true); void fetchNews(); }}
              disabled={loading}
              className="ml-auto flex-shrink-0 flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-50 transition-colors"
            >
              {loading ? (
                <span className="w-3 h-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              ) : (
                '🔄'
              )}
              {t('news.refresh')}
            </button>
          </div>
        </div>
      </div>

      {/* ── Content ───────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-4 py-8">

        {/* Loading skeletons */}
        {loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <p className="text-5xl">⚠️</p>
            <p className="text-slate-600 font-medium">সংবাদ লোড হয়নি</p>
            <p className="text-slate-400 text-sm">{error}</p>
            <button
              onClick={() => { setLoading(true); void fetchNews(); }}
              className="text-sm bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors"
            >
              আবার চেষ্টা করুন
            </button>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <p className="text-5xl">📭</p>
            <p className="text-slate-600 font-medium">
              {news.length === 0 ? 'আজ কোনো আইনি সংবাদ নেই' : 'এই ফিল্টারে কোনো সংবাদ নেই'}
            </p>
            {news.length > 0 && (
              <button
                onClick={() => { setActiveCategory('সব'); setActiveSource('সব'); }}
                className="text-sm text-blue-600 hover:underline"
              >
                সব সংবাদ দেখুন
              </button>
            )}
          </div>
        )}

        {/* News grid */}
        {!loading && !error && filtered.length > 0 && (
          <>
            <p className="text-xs text-slate-400 mb-5">
              {filtered.length} টি সংবাদ
              {activeCategory !== 'সব' && ` · বিভাগ: ${activeCategory}`}
              {activeSource !== 'সব' && ` · সূত্র: ${activeSource}`}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {filtered.map((item) => (
                <NewsCard key={item.id} item={item} />
              ))}
            </div>
          </>
        )}

      </div>

      {/* ── Ask AI CTA ────────────────────────────────────────────────── */}
      <section className="bg-blue-900 mt-4">
        <div className="max-w-3xl mx-auto px-4 py-12 text-center">
          <h2 className="text-xl sm:text-2xl font-bold text-white mb-3">
            সংবাদে উল্লিখিত আইন সম্পর্কে জানতে চান?
          </h2>
          <p className="text-blue-200 text-sm mb-6">
            AI Lawyer আপনাকে বাংলাদেশের যেকোনো আইন সম্পর্কে সহজ ভাষায় বুঝিয়ে দেবে
          </p>
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 bg-white hover:bg-blue-50 text-blue-800 font-bold px-7 py-3.5 rounded-xl text-base transition-colors shadow-md"
          >
            💬 AI-কে জিজ্ঞেস করুন →
          </Link>
        </div>
      </section>

      <footer className="border-t py-6 text-center text-sm text-slate-400 mt-0">
        <p>⚠️ হ্যালো এ্যাডভকেট আইনি পরামর্শ নয় — গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর সাথে যোগাযোগ করুন।</p>
      </footer>
    </div>
  );
}
