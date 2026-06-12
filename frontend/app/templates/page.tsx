'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import NavBar from '@/components/NavBar';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Template {
  id: string;
  title: string;
  title_en: string | null;
  category: string;
  description: string | null;
  is_pro: boolean;
  field_count: number;
  usage_count: number;
}

// ─── Category config ──────────────────────────────────────────────────────────

const CATEGORY_TABS = [
  { key: '',         label: 'সব',          icon: '📋' },
  { key: 'land',     label: 'জমি',         icon: '🏡' },
  { key: 'family',   label: 'পারিবারিক',   icon: '👨‍👩‍👧' },
  { key: 'business', label: 'ব্যবসায়িক',  icon: '💼' },
  { key: 'labor',    label: 'শ্রম',         icon: '⚒️' },
  { key: 'other',    label: 'অন্যান্য',    icon: '📄' },
] as const;

const CATEGORY_COLORS: Record<string, string> = {
  land:     'bg-emerald-100 text-emerald-700',
  family:   'bg-pink-100 text-pink-700',
  business: 'bg-blue-100 text-blue-700',
  labor:    'bg-amber-100 text-amber-700',
  other:    'bg-purple-100 text-purple-700',
};

const CATEGORY_ICONS: Record<string, string> = {
  land:     '🏡',
  family:   '👨‍👩‍👧',
  business: '💼',
  labor:    '⚒️',
  other:    '📄',
};

// ─── Components ───────────────────────────────────────────────────────────────

function TemplateCard({ t }: { t: Template }) {
  const colorClass = CATEGORY_COLORS[t.category] ?? 'bg-slate-100 text-slate-700';
  const icon       = CATEGORY_ICONS[t.category] ?? '📄';

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-emerald-300 transition-all flex flex-col">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center text-xl flex-shrink-0 ${colorClass}`}>
          {icon}
        </div>
        {t.is_pro && (
          <span className="flex-shrink-0 px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-bold rounded-full border border-amber-200">
            PRO
          </span>
        )}
      </div>

      <h3 className="font-semibold text-slate-800 text-base mb-1 leading-snug">{t.title}</h3>
      {t.title_en && (
        <p className="text-xs text-slate-400 mb-2">{t.title_en}</p>
      )}
      {t.description && (
        <p className="text-sm text-slate-500 leading-relaxed mb-4 flex-1">{t.description}</p>
      )}

      <div className="mt-auto">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-slate-400">
            📝 {t.field_count}টি তথ্য প্রয়োজন
          </span>
          {t.usage_count > 0 && (
            <span className="text-xs text-slate-400">
              {t.usage_count.toLocaleString('bn-BD')}× ব্যবহৃত
            </span>
          )}
        </div>
        <Link
          href={`/templates/${t.id}`}
          className="block w-full text-center py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-xl transition-colors"
        >
          ব্যবহার করুন →
        </Link>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TemplatesPage() {
  const [templates,   setTemplates]   = useState<Template[]>([]);
  const [activeTab,   setActiveTab]   = useState('');
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState('');

  useEffect(() => {
    setLoading(true);
    const url = activeTab
      ? `${API}/api/templates?category=${activeTab}`
      : `${API}/api/templates`;

    fetch(url)
      .then(r => r.json())
      .then(data => setTemplates(data as Template[]))
      .catch(() => setError('টেমপ্লেট লোড করতে সমস্যা হয়েছে।'))
      .finally(() => setLoading(false));
  }, [activeTab]);

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section
        className="px-4 py-14 text-center"
        style={{ background: 'linear-gradient(135deg, #064e3b 0%, #065f46 60%, #047857 100%)' }}
      >
        <div className="max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-white/10 text-emerald-200 text-xs font-medium px-3 py-1.5 rounded-full mb-5 border border-white/20">
            <span>✨</span> AI-চালিত দলিল প্রস্তুতকারী
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-4 leading-tight">
            আইনি দলিল তৈরি করুন
          </h1>
          <p className="text-emerald-100 text-base sm:text-lg leading-relaxed">
            AI-এর সাহায্যে পেশাদার আইনি দলিল তৈরি করুন — মিনিটের মধ্যে
          </p>
          <div className="flex items-center justify-center gap-6 mt-7 text-emerald-200 text-sm">
            <span>📝 ৮টি টেমপ্লেট</span>
            <span className="opacity-40">|</span>
            <span>🇧🇩 বাংলাদেশ আইন</span>
            <span className="opacity-40">|</span>
            <span>⚡ তাৎক্ষণিক</span>
          </div>
        </div>
      </section>

      <div className="max-w-6xl mx-auto px-4 py-8">

        {/* ── Category filter ──────────────────────────────────────────────────── */}
        <div className="flex flex-wrap gap-2 mb-8">
          {CATEGORY_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-white text-slate-600 border border-slate-200 hover:border-emerald-300 hover:text-emerald-700'
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── Content ─────────────────────────────────────────────────────────── */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-10 h-10 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="py-12 text-center text-slate-500 text-sm">{error}</div>
        ) : templates.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-sm">এই বিভাগে কোনো টেমপ্লেট নেই।</div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {templates.map(t => <TemplateCard key={t.id} t={t} />)}
          </div>
        )}

        {/* ── Info banner ──────────────────────────────────────────────────────── */}
        <div className="mt-10 bg-amber-50 border border-amber-200 rounded-2xl p-5 flex gap-4">
          <span className="text-2xl flex-shrink-0">⚠️</span>
          <div>
            <p className="text-sm font-semibold text-amber-800 mb-1">গুরুত্বপূর্ণ বিজ্ঞপ্তি</p>
            <p className="text-sm text-amber-700 leading-relaxed">
              AI-তৈরি দলিলগুলি খসড়া হিসেবে বিবেচনা করুন। চূড়ান্ত করার এবং স্বাক্ষর/নিবন্ধনের আগে
              অবশ্যই একজন যোগ্য আইনজীবীর পরামর্শ নিন।
            </p>
          </div>
        </div>
      </div>

      <footer className="border-t py-6 text-center text-sm text-slate-400 mt-4">
        <p>⚠️ হ্যালো এ্যাডভকেট আইনি পরামর্শ নয় — গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর সাথে যোগাযোগ করুন।</p>
      </footer>
    </div>
  );
}
