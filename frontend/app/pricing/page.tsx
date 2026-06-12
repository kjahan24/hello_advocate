'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export default function PricingPage() {
  const { t } = useLanguage();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [token, setToken]         = useState<string | null>(null);

  useEffect(() => {
    setToken(localStorage.getItem('token'));
  }, []);

  // ── Feature lists (inside component so t() works) ─────────────────────────

  const FREE_FEATURES = [
    t('pricing.freeFeature1'),
    t('pricing.freeFeature2'),
    t('pricing.freeFeature3'),
    t('pricing.freeFeature4'),
  ];

  const FREE_EXCLUDES = [
    t('pricing.freeExclude1'),
    t('pricing.freeExclude2'),
  ];

  const PRO_FEATURES = [
    t('pricing.proFeature1'),
    t('pricing.proFeature2'),
    t('pricing.proFeature3'),
    t('pricing.proFeature4'),
    t('pricing.proFeature5'),
    t('pricing.proFeature6'),
  ];

  const STUDENT_FEATURES = [
    t('pricing.studentFeature1'),
    t('pricing.studentFeature2'),
    t('pricing.studentFeature3'),
    t('pricing.studentFeature4'),
    t('pricing.studentFeature5'),
    t('pricing.studentFeature6'),
    t('pricing.studentFeature7'),
  ];

  const handleSubscribe = async () => {
    if (!token) {
      window.location.href = '/login?redirect=/pricing';
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/payments/initiate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      const data: unknown = await res.json();

      if (!res.ok || data === null || typeof data !== 'object') {
        const detail =
          'detail' in (data as object)
            ? String((data as Record<string, unknown>).detail)
            : t('common.error');
        setError(detail);
        return;
      }

      const { gateway_url } = data as { gateway_url: string };
      window.location.href = gateway_url;
    } catch {
      setError(t('common.error'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* Hero */}
      <section className="bg-emerald-700 py-16 px-4 text-center">
        <h1 className="text-3xl sm:text-5xl font-bold text-white mb-4">{t('pricing.title')}</h1>
        <p className="text-emerald-100 text-lg max-w-xl mx-auto">
          {t('pricing.heroSubtitle')}
        </p>
      </section>

      {/* Cards — 3 columns */}
      <section className="max-w-6xl mx-auto px-4 py-16">
        <div className="grid sm:grid-cols-3 gap-6 items-start">

          {/* ── FREE ─────────────────────────────────────────────────────── */}
          <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm flex flex-col">
            <div className="mb-6">
              <p className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-1">
                {t('pricing.free')}
              </p>
              <div className="flex items-end gap-1">
                <span className="text-4xl font-bold text-slate-800">{t('pricing.freePrice')}</span>
                <span className="text-slate-400 mb-1">{t('pricing.perMonth')}</span>
              </div>
            </div>

            <ul className="space-y-3 flex-1 mb-8">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm text-slate-600">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center text-xs">✓</span>
                  {f}
                </li>
              ))}
              {FREE_EXCLUDES.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm text-slate-300">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-50 text-slate-300 flex items-center justify-center text-xs">✕</span>
                  {f}
                </li>
              ))}
            </ul>

            <Link
              href="/chat"
              className="block text-center bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-6 py-3 rounded-xl transition-colors"
            >
              {t('pricing.getStarted')}
            </Link>
          </div>

          {/* ── PRO ──────────────────────────────────────────────────────── */}
          <div
            className="rounded-2xl p-8 shadow-xl flex flex-col relative overflow-hidden"
            style={{ background: 'linear-gradient(135deg, #064e3b 0%, #065f46 50%, #047857 100%)' }}
          >
            <div className="absolute top-4 right-4 bg-yellow-400 text-yellow-900 text-xs font-bold px-3 py-1 rounded-full">
              {t('pricing.mostPopular')}
            </div>

            <div className="mb-6">
              <p className="text-sm font-semibold text-emerald-300 uppercase tracking-wide mb-1">
                {t('pricing.pro')}
              </p>
              <div className="flex items-end gap-1">
                <span className="text-4xl font-bold text-white">{t('pricing.proPrice')}</span>
                <span className="text-emerald-200 mb-1">{t('pricing.perMonth')}</span>
              </div>
              <p className="text-emerald-300 text-xs mt-1">{t('pricing.securePayment')}</p>
            </div>

            <ul className="space-y-3 flex-1 mb-8">
              {PRO_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm text-emerald-100">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-500/40 text-emerald-300 flex items-center justify-center text-xs">✓</span>
                  {f}
                </li>
              ))}
            </ul>

            {error && (
              <p className="text-red-300 text-sm mb-3 bg-red-900/30 rounded-lg px-3 py-2">{error}</p>
            )}

            <button
              onClick={handleSubscribe}
              disabled={isLoading}
              className="w-full bg-white hover:bg-slate-100 disabled:bg-slate-200 text-emerald-700 font-bold px-6 py-3.5 rounded-xl transition-colors shadow-md text-base"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
                  {t('pricing.processing')}
                </span>
              ) : (
                t('pricing.upgrade')
              )}
            </button>

            {!token && (
              <p className="text-emerald-300 text-xs text-center mt-3">
                {t('pricing.loginToSub')}{' '}
                <Link href="/login?redirect=/pricing" className="underline text-white">
                  {t('pricing.loginLink')}
                </Link>
              </p>
            )}
          </div>

          {/* ── STUDENT ──────────────────────────────────────────────────── */}
          <div className="bg-white border-2 border-blue-200 rounded-2xl p-8 shadow-sm flex flex-col relative overflow-hidden">
            <div className="absolute top-4 right-4 bg-blue-100 text-blue-700 text-xs font-bold px-3 py-1 rounded-full">
              {t('pricing.studentBadge')}
            </div>

            <div className="mb-6">
              <p className="text-sm font-semibold text-blue-500 uppercase tracking-wide mb-1">
                {t('pricing.studentPlan')}
              </p>
              <div className="flex items-end gap-1">
                <span className="text-4xl font-bold text-slate-800">{t('pricing.studentPrice')}</span>
              </div>
              <p className="text-slate-400 text-xs mt-1">{t('pricing.perMonth')}</p>
            </div>

            <ul className="space-y-3 flex-1 mb-8">
              {STUDENT_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm text-slate-600">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs">✓</span>
                  {f}
                </li>
              ))}
            </ul>

            <Link
              href="#"
              className="block text-center bg-blue-600 hover:bg-blue-700 text-white font-bold px-6 py-3 rounded-xl transition-colors shadow-md"
            >
              {t('pricing.applyNow')}
            </Link>
          </div>

        </div>

        {/* Trust note */}
        <p className="text-center text-sm text-slate-400 mt-10">
          {t('pricing.trustNote')}
        </p>
      </section>

      <footer className="border-t py-6 text-center text-sm text-slate-400">
        <p>{t('landing.disclaimer')}</p>
      </footer>
    </div>
  );
}
