'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

interface DashboardStats {
  user: {
    name:              string | null;
    email:             string;
    plan:              string;
    query_count_today: number;
    query_limit:       number;
    joined_at:         string | null;
  };
  subscription: {
    plan:       string;
    status:     string;
    expires_at: string | null;
    is_active:  boolean;
  };
  stats: {
    today_questions: number;
    total_chats:     number;
    total_documents: number;
    upcoming_cases:  number;
  };
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function initials(name: string | null, email: string): string {
  const src = name?.trim() || email;
  return src
    .split(/[\s@]/)
    .filter(Boolean)
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({
  label, value, sub, href,
}: {
  label: string; value: string; sub?: string; href?: string;
}) {
  const inner = (
    <>
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">{label}</p>
      <p className="text-2xl font-bold text-slate-800">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </>
  );
  if (href) {
    return (
      <Link href={href} className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:border-emerald-300 hover:shadow-md transition-all block">
        {inner}
      </Link>
    );
  }
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      {inner}
    </div>
  );
}

function QuickAction({
  href, icon, label, description, highlight,
}: {
  href: string; icon: string; label: string; description: string; highlight?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`flex items-start gap-4 p-5 rounded-2xl border transition-all group ${
        highlight
          ? 'bg-emerald-50 border-emerald-200 hover:bg-emerald-100'
          : 'bg-white border-slate-200 hover:border-emerald-300 hover:shadow-sm'
      }`}
    >
      <span className="text-2xl flex-shrink-0 mt-0.5">{icon}</span>
      <div>
        <p className={`font-semibold text-sm ${highlight ? 'text-emerald-800' : 'text-slate-800'}`}>
          {label}
        </p>
        <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
      </div>
    </Link>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { t } = useLanguage();
  const router = useRouter();

  const [stats,   setStats]   = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.replace('/login?redirect=/dashboard');
      return;
    }

    void fetch(`${API_URL}/api/dashboard/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 401) {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          router.replace('/login?redirect=/dashboard');
          return;
        }
        const data: unknown = await res.json();
        if (!res.ok) {
          setError('ড্যাশবোর্ড লোড করা যায়নি।');
          return;
        }
        setStats(data as DashboardStats);
      })
      .catch(() => setError('সার্ভারের সাথে সংযোগ করা যাচ্ছে না।'))
      .finally(() => setLoading(false));
  }, [router]);

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
  if (error || !stats) {
    return (
      <div className="min-h-screen bg-slate-50">
        <NavBar />
        <div className="flex flex-col items-center justify-center h-[calc(100vh-65px)] gap-4">
          <p className="text-slate-500 text-sm">{error ?? 'ড্যাশবোর্ড লোড করা যায়নি।'}</p>
          <Link href="/chat" className="text-emerald-600 text-sm font-medium hover:underline">
            চ্যাটে যান →
          </Link>
        </div>
      </div>
    );
  }

  const { user, subscription, stats: s } = stats;
  const isPro    = subscription.is_active && subscription.plan === 'pro';
  const displayName = user.name ?? user.email;

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section
        className="px-4 py-10"
        style={{ background: 'linear-gradient(135deg, #064e3b 0%, #065f46 60%, #047857 100%)' }}
      >
        <div className="max-w-4xl mx-auto flex items-center gap-5">
          {/* Avatar */}
          <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center text-white font-bold text-xl flex-shrink-0 border-2 border-white/30">
            {initials(user.name, user.email)}
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-white truncate">
                {t('dashboard.welcome')}, {displayName}!
              </h1>
              {isPro ? (
                <span className="bg-yellow-400 text-yellow-900 text-xs font-bold px-2.5 py-1 rounded-full flex-shrink-0">
                  প্রো ⭐
                </span>
              ) : (
                <span className="bg-white/20 text-white/80 text-xs font-semibold px-2.5 py-1 rounded-full flex-shrink-0">
                  বিনামূল্যে
                </span>
              )}
            </div>
            <p className="text-emerald-200 text-sm mt-1">{user.email}</p>
          </div>
        </div>
      </section>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">

        {/* ── Stat cards ───────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="আজকের প্রশ্ন"
            value={isPro ? String(s.today_questions) : `${s.today_questions} / ${user.query_limit}`}
            sub={isPro ? 'সীমাহীন' : `${user.query_limit - s.today_questions} বাকি`}
          />
          <StatCard
            label={t('dashboard.totalChats')}
            value={s.total_chats > 0 ? String(s.total_chats) : '০'}
            href="/history"
          />
          <StatCard
            label={t('dashboard.documents')}
            value={s.total_documents > 0 ? String(s.total_documents) : '০'}
          />
          <StatCard
            label={t('dashboard.subscription')}
            value={isPro ? 'প্রো' : 'বিনামূল্যে'}
            sub={isPro && subscription.expires_at ? `মেয়াদ: ${formatDate(subscription.expires_at)}` : undefined}
          />
          <div className={`rounded-2xl p-5 shadow-sm border ${s.upcoming_cases > 0 ? 'bg-red-50 border-red-200' : 'bg-white border-slate-200'}`}>
            <p className={`text-xs font-medium uppercase tracking-wide mb-2 ${s.upcoming_cases > 0 ? 'text-red-400' : 'text-slate-400'}`}>আসন্ন মামলা</p>
            <p className={`text-2xl font-bold ${s.upcoming_cases > 0 ? 'text-red-700' : 'text-slate-800'}`}>{s.upcoming_cases > 0 ? String(s.upcoming_cases) : '০'}</p>
            <p className={`text-xs mt-1 ${s.upcoming_cases > 0 ? 'text-red-500' : 'text-slate-400'}`}>{s.upcoming_cases > 0 ? '৭ দিনের মধ্যে ⚠️' : 'কোনো আসন্ন তারিখ নেই'}</p>
          </div>
        </div>

        {/* ── Quick actions ─────────────────────────────────────────────────── */}
        <div>
          <h2 className="text-base font-semibold text-slate-700 mb-4">দ্রুত অ্যাকশন</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <QuickAction
              href="/chat"
              icon="💬"
              label="আইনি প্রশ্ন করুন"
              description="যেকোনো আইনি বিষয়ে AI সহায়তা নিন"
            />
            <QuickAction
              href="/document"
              icon="📄"
              label="ডকুমেন্ট বিশ্লেষণ"
              description="PDF বা DOCX ফাইল আপলোড করে বিশ্লেষণ করুন"
            />
            <QuickAction
              href="/history"
              icon="📜"
              label="চ্যাট ইতিহাস"
              description="আপনার আগের সব কথোপকথন দেখুন"
            />
            {!isPro && (
              <QuickAction
                href="/pricing"
                icon="⭐"
                label="প্রো সাবস্ক্রিপশন"
                description="সীমাহীন প্রশ্ন, ডকুমেন্ট বিশ্লেষণ ও আরও অনেক কিছু"
                highlight
              />
            )}
            <QuickAction
              href="/court-cases"
              icon="📅"
              label="মামলার তারিখ"
              description="আপনার মামলার গুরুত্বপূর্ণ তারিখ ট্র্যাক করুন"
            />
            <QuickAction
              href="/templates"
              icon="📝"
              label="দলিল টেমপ্লেট"
              description="AI দিয়ে ভাড়া চুক্তি, উইল, আমমোক্তারনামা তৈরি করুন"
            />
            <QuickAction
              href="/land"
              icon="⚖️"
              label="আইনি সেবা"
              description="জমি, পারিবারিক, শ্রম, ব্যবসায়িক আইন"
            />
          </div>
        </div>

        {/* ── Subscription card ─────────────────────────────────────────────── */}
        {isPro ? (
          <div className="bg-white border border-emerald-200 rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full" />
                <p className="font-semibold text-slate-800">প্রো সদস্য ✅</p>
              </div>
              {subscription.expires_at && (
                <p className="text-sm text-slate-500">
                  সাবস্ক্রিপশন মেয়াদ: <strong>{formatDate(subscription.expires_at)}</strong>
                </p>
              )}
            </div>
            <Link
              href="/pricing"
              className="flex-shrink-0 text-sm bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors"
            >
              সাবস্ক্রিপশন নবায়ন করুন
            </Link>
          </div>
        ) : (
          <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <p className="font-semibold text-slate-800 mb-1">
                আপনি বিনামূল্যে প্ল্যানে আছেন
              </p>
              <p className="text-sm text-slate-500">
                প্রতিদিন {user.query_limit}টি প্রশ্ন • ডকুমেন্ট বিশ্লেষণ সীমিত
              </p>
            </div>
            <Link
              href="/pricing"
              className="flex-shrink-0 text-sm bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors shadow-sm"
            >
              প্রো-তে আপগ্রেড করুন →
            </Link>
          </div>
        )}

      </div>

      <footer className="border-t py-6 text-center text-sm text-slate-400 mt-4">
        <p>⚠️ হ্যালো এ্যাডভকেট আইনি পরামর্শ নয় — গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর সাথে যোগাযোগ করুন।</p>
      </footer>
    </div>
  );
}
