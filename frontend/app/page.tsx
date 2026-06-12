'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface NewsItem {
  id:           string;
  title:        string;
  summary:      string;
  link:         string;
  source:       string;
  published_at: string;
  category:     string;
}

const SOURCE_COLORS: Record<string, string> = {
  'প্রথম আলো':    'bg-red-100 text-red-700',
  'বিডি প্রতিদিন': 'bg-blue-100 text-blue-700',
  'যুগান্তর':      'bg-green-100 text-green-700',
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const { t } = useLanguage();
  const [latestNews, setLatestNews] = useState<NewsItem[]>([]);

  useEffect(() => {
    void fetch(`${API_URL}/api/news`)
      .then(r => r.ok ? r.json() : null)
      .then((data: { news: NewsItem[] } | null) => {
        if (data?.news) setLatestNews(data.news.slice(0, 3));
      })
      .catch(() => { /* silently ignore on landing page */ });
  }, []);

  const scrollToFeatures = () => {
    document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
  };

  // ── Data arrays (inside component so t() is available) ───────────────────────

  const FEATURES = [
    { icon: '🤖', title: t('landing.feature1Title'), desc: t('landing.feature1Desc') },
    { icon: '📄', title: t('landing.feature2Title'), desc: t('landing.feature2Desc') },
    { icon: '⚖️', title: t('landing.feature3Title'), desc: t('landing.feature3Desc') },
    { icon: '📅', title: t('landing.feature4Title'), desc: t('landing.feature4Desc') },
    { icon: '🔒', title: t('landing.feature5Title'), desc: t('landing.feature5Desc') },
    { icon: '💰', title: t('landing.feature6Title'), desc: t('landing.feature6Desc') },
  ];

  const STEPS = [
    { icon: '📝', num: t('landing.stepNum1'), title: t('landing.step1Title'), desc: t('landing.step1Desc') },
    { icon: '🔍', num: t('landing.stepNum2'), title: t('landing.step2Title'), desc: t('landing.step2Desc') },
    { icon: '✅', num: t('landing.stepNum3'), title: t('landing.step3Title'), desc: t('landing.step3Desc') },
  ];

  const CATEGORIES = [
    { icon: '🏡', title: t('landing.cat1Title'), desc: t('landing.cat1Desc'), href: '/land' },
    { icon: '👨‍👩‍👧', title: t('landing.cat2Title'), desc: t('landing.cat2Desc'), href: '/family' },
    { icon: '💼', title: t('landing.cat3Title'), desc: t('landing.cat3Desc'), href: '/business' },
    { icon: '⚒️', title: t('landing.cat4Title'), desc: t('landing.cat4Desc'), href: '/labor' },
    { icon: '⚖️', title: t('landing.cat5Title'), desc: t('landing.cat5Desc'), href: '/chat?topic=criminal' },
    { icon: '🛒', title: t('landing.cat6Title'), desc: t('landing.cat6Desc'), href: '/consumer' },
  ];

  const FREE_FEATURES = [
    t('landing.freeFeature1'),
    t('landing.freeFeature2'),
    t('landing.freeFeature3'),
    t('landing.freeFeature4'),
  ];

  const PRO_FEATURES = [
    t('landing.proFeature1'),
    t('landing.proFeature2'),
    t('landing.proFeature3'),
    t('landing.proFeature4'),
    t('landing.proFeature5'),
  ];

  const STUDENT_FEATURES = [
    t('landing.proFeature1'),
    t('landing.proFeature2'),
    t('pricing.studentFeature7'),
  ];

  return (
    <div className="min-h-screen bg-white">
      <NavBar />

      {/* ════════════════════════════════════════════════════════════════════
          1. HERO
      ════════════════════════════════════════════════════════════════════ */}
      <section className="relative min-h-screen bg-gradient-to-br from-[#064e3b] to-[#065f46] flex flex-col items-center justify-center text-center px-6 pt-20 pb-32 overflow-hidden">
        {/* Decorative blobs */}
        <div className="absolute top-24 left-8 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-24 right-8 w-96 h-96 bg-emerald-400/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIvPjwvZz48L2c+PC9zdmc+')] opacity-40 pointer-events-none" />

        <div className="relative z-10 max-w-4xl mx-auto">
          {/* Top badge */}
          <div className="inline-flex items-center gap-2.5 bg-white/10 border border-white/20 text-white/90 text-sm font-medium px-5 py-2.5 rounded-full mb-10 backdrop-blur-sm">
            <span className="text-base">🇧🇩</span>
            <span>{t('landing.badge')}</span>
          </div>

          {/* Main headline */}
          <h1 className="text-5xl sm:text-7xl font-extrabold text-white leading-[1.1] tracking-tight mb-3">
            {t('landing.heroTitle1')}
          </h1>
          <h2 className="text-5xl sm:text-7xl font-extrabold text-[#34d399] leading-[1.1] tracking-tight mb-8">
            {t('landing.heroTitle2')}
          </h2>

          {/* Description */}
          <p className="text-lg sm:text-xl text-white/75 max-w-2xl mx-auto mb-12 leading-relaxed">
            {t('landing.heroSubtitle')}
          </p>

          {/* CTA buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-20">
            <Link
              href="/chat"
              className="inline-flex items-center justify-center gap-2 bg-white text-emerald-800 font-bold px-9 py-4 rounded-xl text-lg hover:bg-emerald-50 transition-all shadow-2xl shadow-black/30 hover:shadow-black/40 hover:scale-[1.02] active:scale-[0.99]"
            >
              {t('landing.startFree')}
            </Link>
            <button
              onClick={scrollToFeatures}
              className="inline-flex items-center justify-center gap-2 border-2 border-white/30 hover:border-white/60 text-white font-semibold px-9 py-4 rounded-xl text-lg transition-all backdrop-blur-sm hover:bg-white/5"
            >
              {t('landing.learnMore')}
            </button>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-4 max-w-sm sm:max-w-md mx-auto">
            {[
              { valueKey: 'landing.statsLawsNum',     labelKey: 'landing.statsLaws' },
              { valueKey: 'landing.statsSectionsNum',  labelKey: 'landing.statsSections' },
              { valueKey: 'landing.statsTime',         labelKey: 'landing.statsAvailable' },
            ].map((s) => (
              <div key={s.labelKey} className="text-center px-2">
                <p className="text-2xl sm:text-4xl font-bold text-white">{t(s.valueKey)}</p>
                <p className="text-emerald-300/90 text-xs sm:text-sm mt-1 leading-tight">{t(s.labelKey)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Scroll caret */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce text-white/30">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          2. FEATURES
      ════════════════════════════════════════════════════════════════════ */}
      <section id="features" className="bg-white py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-emerald-600 font-semibold text-sm uppercase tracking-widest mb-3">{t('landing.featuresLabel')}</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900">{t('landing.featuresTitle')}</h2>
            <div className="w-16 h-1 bg-emerald-500 rounded-full mx-auto mt-5" />
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="group bg-white border border-slate-100 hover:border-emerald-200 rounded-2xl p-7 shadow-sm hover:shadow-lg transition-all duration-200"
              >
                <div className="text-4xl mb-5">{f.icon}</div>
                <h3 className="text-lg font-bold text-slate-800 mb-2 group-hover:text-emerald-700 transition-colors">
                  {f.title}
                </h3>
                <p className="text-slate-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          3. HOW IT WORKS
      ════════════════════════════════════════════════════════════════════ */}
      <section className="bg-[#f9fafb] py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-emerald-600 font-semibold text-sm uppercase tracking-widest mb-3">{t('landing.processLabel')}</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900">{t('landing.processTitle')}</h2>
            <div className="w-16 h-1 bg-emerald-500 rounded-full mx-auto mt-5" />
          </div>

          <div className="flex flex-col sm:flex-row items-start justify-between gap-6">
            {STEPS.map((step, i) => (
              <React.Fragment key={step.title}>
                <div className="flex-1 flex flex-col items-center text-center">
                  <div className="w-20 h-20 rounded-2xl bg-emerald-600 flex items-center justify-center text-4xl shadow-lg shadow-emerald-600/25 mb-5">
                    {step.icon}
                  </div>
                  <p className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-2">
                    {t('landing.stepLabel')} {step.num}
                  </p>
                  <h3 className="text-xl font-bold text-slate-800 mb-2">{step.title}</h3>
                  <p className="text-slate-500 text-sm leading-relaxed max-w-[220px]">{step.desc}</p>
                </div>
                {i < 2 && (
                  <div className="hidden sm:flex items-center justify-center flex-shrink-0 mt-8 text-slate-300">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          4. LEGAL CATEGORIES
      ════════════════════════════════════════════════════════════════════ */}
      <section className="bg-white py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-emerald-600 font-semibold text-sm uppercase tracking-widest mb-3">{t('landing.servicesLabel')}</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900">{t('landing.servicesTitle')}</h2>
            <div className="w-16 h-1 bg-emerald-500 rounded-full mx-auto mt-5" />
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {CATEGORIES.map((cat) => (
              <Link
                key={cat.href}
                href={cat.href}
                className="group flex items-start gap-4 bg-white border border-slate-100 hover:border-emerald-300 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-200"
              >
                <span className="text-4xl flex-shrink-0 leading-none mt-0.5">{cat.icon}</span>
                <div>
                  <h3 className="font-bold text-slate-800 text-base mb-1 group-hover:text-emerald-700 transition-colors">
                    {cat.title}
                  </h3>
                  <p className="text-slate-500 text-sm leading-snug mb-2">{cat.desc}</p>
                  <span className="text-xs font-semibold text-emerald-600 group-hover:text-emerald-700 transition-colors">
                    {t('landing.explore')}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          5. LATEST LEGAL NEWS WIDGET
      ════════════════════════════════════════════════════════════════════ */}
      {latestNews.length > 0 && (
        <section className="bg-[#f9fafb] py-20 px-6">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-10 flex-wrap gap-4">
              <div>
                <p className="text-blue-700 font-semibold text-sm uppercase tracking-widest mb-2">{t('landing.newsLabel')}</p>
                <h2 className="text-3xl font-bold text-slate-900">{t('landing.latestNewsTitle')}</h2>
              </div>
              <Link
                href="/news"
                className="text-sm font-semibold text-blue-700 hover:text-blue-900 border border-blue-200 hover:border-blue-400 px-4 py-2 rounded-xl transition-colors"
              >
                {t('landing.viewAllNews')}
              </Link>
            </div>
            <div className="grid sm:grid-cols-3 gap-5">
              {latestNews.map((item) => (
                <div
                  key={item.id}
                  className="bg-white border border-slate-100 hover:border-blue-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-200"
                >
                  <div className="flex items-center gap-2 mb-3 flex-wrap">
                    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${SOURCE_COLORS[item.source] ?? 'bg-slate-100 text-slate-600'}`}>
                      {item.source}
                    </span>
                    <span className="text-xs text-slate-400 ml-auto">{item.category}</span>
                  </div>
                  <h3 className="font-bold text-slate-800 text-sm leading-snug mb-2 line-clamp-2">
                    {item.title}
                  </h3>
                  {item.summary && (
                    <p className="text-slate-500 text-xs leading-relaxed line-clamp-2 mb-3">
                      {item.summary}
                    </p>
                  )}
                  {item.link?.startsWith('http') && (
                    <a
                      href={item.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors"
                    >
                      {t('landing.readMore')}
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════
          6. PRICING PREVIEW
      ════════════════════════════════════════════════════════════════════ */}
      <section className="bg-gradient-to-br from-[#064e3b] to-[#065f46] py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <p className="text-emerald-300 font-semibold text-sm uppercase tracking-widest mb-3">{t('pricing.title')}</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-white">{t('landing.pricingTitle')}</h2>
            <p className="text-emerald-200/80 mt-3 text-base">{t('landing.pricingSubtitle')}</p>
          </div>

          <div className="grid sm:grid-cols-3 gap-5">
            {/* FREE */}
            <div className="bg-white/10 border border-white/20 rounded-2xl p-7 backdrop-blur-sm flex flex-col">
              <p className="text-white font-bold text-lg mb-1">{t('pricing.free')}</p>
              <p className="text-3xl font-extrabold text-white mb-1">
                {t('pricing.freePrice')}
              </p>
              <p className="text-white/50 text-sm mb-5">{t('pricing.perMonth')}</p>
              <ul className="space-y-2.5 flex-1 mb-7">
                {FREE_FEATURES.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-white/80">
                    <span className="text-emerald-300 font-bold flex-shrink-0">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/chat"
                className="block text-center bg-white/15 hover:bg-white/25 border border-white/30 text-white font-semibold py-3 rounded-xl transition-colors text-sm"
              >
                {t('landing.startNow')}
              </Link>
            </div>

            {/* PRO */}
            <div className="bg-white rounded-2xl p-7 shadow-2xl relative flex flex-col">
              <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-emerald-500 text-white text-xs font-bold px-5 py-1.5 rounded-full shadow">
                {t('landing.popular')}
              </span>
              <p className="text-emerald-800 font-bold text-lg mb-1">{t('pricing.pro')}</p>
              <p className="text-3xl font-extrabold text-slate-900 mb-1">
                {t('pricing.proPrice')}
              </p>
              <p className="text-slate-400 text-sm mb-5">{t('pricing.perMonth')}</p>
              <ul className="space-y-2.5 flex-1 mb-7">
                {PRO_FEATURES.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-slate-700">
                    <span className="text-emerald-500 font-bold flex-shrink-0">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/pricing"
                className="block text-center bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition-colors shadow-md text-sm"
              >
                {t('landing.subscribe')}
              </Link>
            </div>

            {/* STUDENT */}
            <div className="bg-white/10 border-2 border-blue-300/40 rounded-2xl p-7 backdrop-blur-sm flex flex-col">
              <span className="inline-block bg-blue-400/20 text-blue-200 text-xs font-bold px-3 py-1 rounded-full mb-3 self-start">
                {t('pricing.studentBadge')}
              </span>
              <p className="text-white font-bold text-lg mb-1">{t('pricing.studentPlan')}</p>
              <p className="text-3xl font-extrabold text-white mb-1">
                {t('pricing.studentPrice')}
              </p>
              <p className="text-white/50 text-sm mb-5">{t('pricing.perMonth')}</p>
              <ul className="space-y-2.5 flex-1 mb-7">
                {STUDENT_FEATURES.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-white/80">
                    <span className="text-blue-300 font-bold flex-shrink-0">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/pricing"
                className="block text-center bg-blue-500/30 hover:bg-blue-500/50 border border-blue-300/40 text-white font-semibold py-3 rounded-xl transition-colors text-sm"
              >
                {t('pricing.applyNow')}
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          7. FINAL CTA
      ════════════════════════════════════════════════════════════════════ */}
      <section className="bg-white py-28 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-4xl sm:text-5xl font-extrabold text-slate-900 mb-4 leading-tight">
            {t('landing.ctaTitle1')}<br />
            <span className="text-emerald-600">{t('landing.ctaTitle2')}</span>
          </h2>
          <p className="text-slate-500 text-lg mb-10 leading-relaxed">
            {t('landing.ctaSubtitle')}
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-10 py-4 rounded-xl text-lg transition-all shadow-lg shadow-emerald-600/30 hover:shadow-emerald-600/40 hover:scale-[1.02] active:scale-[0.99]"
          >
            {t('landing.ctaButton')}
          </Link>
          <p className="text-slate-400 text-sm mt-5">{t('landing.noCard')}</p>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          8. FOOTER
      ════════════════════════════════════════════════════════════════════ */}
      <footer className="bg-slate-900 text-slate-400 py-12 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid sm:grid-cols-3 gap-8 mb-10">
            {/* Brand */}
            <div>
              <div className="flex items-center gap-2.5 mb-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center flex-shrink-0">
                  <span className="text-white font-bold text-sm">আ</span>
                </div>
                <span className="text-white font-bold text-base">Hello Advocate</span>
              </div>
              <p className="text-sm leading-relaxed text-slate-500">
                {t('landing.footerTagline')}
              </p>
            </div>

            {/* Links */}
            <div>
              <p className="text-white font-semibold text-sm mb-3">{t('landing.footerServices')}</p>
              <ul className="space-y-2 text-sm">
                {[
                  { labelKey: 'landing.footerLegalService', href: '/chat' },
                  { labelKey: 'landing.footerDocuments',    href: '/document' },
                  { labelKey: 'landing.footerFindLawyer',   href: '/lawyers' },
                  { labelKey: 'landing.footerPricing',      href: '/pricing' },
                ].map((l) => (
                  <li key={l.href}>
                    <Link href={l.href} className="hover:text-emerald-400 transition-colors">
                      {t(l.labelKey)}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            {/* Account */}
            <div>
              <p className="text-white font-semibold text-sm mb-3">{t('landing.footerAccount')}</p>
              <ul className="space-y-2 text-sm">
                {[
                  { labelKey: 'landing.footerRegister',  href: '/register' },
                  { labelKey: 'landing.footerLogin',     href: '/login' },
                  { labelKey: 'landing.footerDashboard', href: '/dashboard' },
                  { labelKey: 'landing.footerHistory',   href: '/history' },
                ].map((l) => (
                  <li key={l.href}>
                    <Link href={l.href} className="hover:text-emerald-400 transition-colors">
                      {t(l.labelKey)}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="border-t border-slate-800 pt-8 space-y-2">
            <p className="text-sm text-center">
              {t('landing.copyright')}
            </p>
            <p className="text-xs text-slate-600 text-center">
              {t('landing.disclaimer')}
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
