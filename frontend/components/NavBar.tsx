'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useLanguage } from '@/contexts/LanguageContext';
import LanguageToggle from '@/components/LanguageToggle';

// ─── services menu ────────────────────────────────────────────────────────────

const SERVICES_HREFS = [
  { href: '/land',      icon: '🏡', key: 'land'     },
  { href: '/family',    icon: '👨‍👩‍👧', key: 'family'   },
  { href: '/business',  icon: '💼', key: 'business'  },
  { href: '/labor',     icon: '⚒️', key: 'labor'     },
  { href: '/consumer',  icon: '🛡️', key: 'consumer'  },
] as const;

const MOBILE_LINKS_CONFIG = [
  { href: '/document',    icon: '📄', tKey: 'navbar.document'  },
  { href: '/agent',       icon: '🤖', tKey: 'navbar.agent'     },
  { href: '/court-cases', icon: '📅', tKey: 'navbar.cases'     },
  { href: '/lawyers',     icon: '⚖️', tKey: 'navbar.lawyers'   },
  { href: '/news',        icon: '📰', tKey: 'navbar.news'      },
  { href: '/pricing',     icon: '💳', tKey: 'navbar.pricing'   },
] as const;

// ─── avatar ───────────────────────────────────────────────────────────────────

function UserAvatar({ name }: { name: string }) {
  const initials = name
    .trim()
    .split(/[\s@]/)
    .filter(Boolean)
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
  return (
    <div className="w-9 h-9 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
      {initials || '?'}
    </div>
  );
}

// ─── stored user shape ────────────────────────────────────────────────────────

interface StoredUser {
  name?: string | null;
  email?: string;
  is_admin?: boolean;
}

// ─── navbar ───────────────────────────────────────────────────────────────────

export default function NavBar() {
  const { t } = useLanguage();

  const [storedUser,   setStoredUser]   = useState<StoredUser | null>(null);
  const [userOpen,     setUserOpen]     = useState(false);
  const [servicesOpen, setServicesOpen] = useState(false);
  const [mobileOpen,   setMobileOpen]   = useState(false);

  const userRef     = useRef<HTMLDivElement>(null);
  const servicesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;
    const raw = localStorage.getItem('user');
    if (raw) {
      try {
        setStoredUser(JSON.parse(raw) as StoredUser);
      } catch {
        setStoredUser({});
      }
    } else {
      setStoredUser({});
    }
  }, []);

  useEffect(() => {
    if (!userOpen) return;
    function onMouseDown(e: MouseEvent) {
      if (userRef.current && !userRef.current.contains(e.target as Node)) {
        setUserOpen(false);
      }
    }
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [userOpen]);

  useEffect(() => {
    if (!servicesOpen) return;
    function onMouseDown(e: MouseEvent) {
      if (servicesRef.current && !servicesRef.current.contains(e.target as Node)) {
        setServicesOpen(false);
      }
    }
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [servicesOpen]);

  useEffect(() => {
    if (!mobileOpen) return;
    const close = () => setMobileOpen(false);
    window.addEventListener('resize', close);
    return () => window.removeEventListener('resize', close);
  }, [mobileOpen]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
  };

  const displayName = storedUser?.name?.trim() || storedUser?.email || '';
  const closeMobile = () => setMobileOpen(false);

  return (
    <nav className="border-b bg-white/95 backdrop-blur-md sticky top-0 z-40">

      {/* ── Main row ──────────────────────────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">

        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 flex-shrink-0" onClick={closeMobile}>
          <div className="w-9 h-9 rounded-xl bg-emerald-600 flex items-center justify-center shadow-sm">
            <span className="text-white font-bold text-sm">আ</span>
          </div>
          <span className="font-bold text-slate-800 text-lg">হ্যালো এ্যাডভকেট</span>
        </Link>

        {/* Centre — navigation (desktop only) */}
        <div className="hidden md:flex items-center flex-1 justify-center gap-1">
          <div ref={servicesRef} className="relative">
            <button
              onClick={() => setServicesOpen((prev) => !prev)}
              className={`flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-xl transition-colors ${
                servicesOpen
                  ? 'bg-slate-100 text-slate-900'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              {t('navbar.legalServices')}
              <svg
                className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-150 ${servicesOpen ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {servicesOpen && (
              <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1.5 w-52 bg-white rounded-xl border border-slate-200 shadow-lg py-1.5 z-50">
                {SERVICES_HREFS.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setServicesOpen(false)}
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    <span>{item.icon}</span>
                    {t(`services.${item.key}`)}
                  </Link>
                ))}
                <Link
                  href="/templates"
                  onClick={() => setServicesOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <span>📝</span>
                  দলিল টেমপ্লেট
                </Link>
              </div>
            )}
          </div>

          <Link
            href="/document"
            className="flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            📄 {t('navbar.document')}
          </Link>

          <Link
            href="/agent"
            className="flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            🤖 {t('navbar.agent')}
          </Link>

          <Link
            href="/court-cases"
            className="flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            📅 {t('navbar.cases')}
          </Link>

          <Link
            href="/lawyers"
            className="flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            ⚖️ {t('navbar.lawyers')}
          </Link>

          <Link
            href="/news"
            className="flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            📰 {t('navbar.news')}
          </Link>

          <Link
            href="/pricing"
            className="flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            {t('navbar.pricing')}
          </Link>
        </div>

        {/* Right — language toggle + auth */}
        <div className="flex items-center gap-2 flex-shrink-0">

          {/* Language toggle (desktop) */}
          <div className="hidden md:block">
            <LanguageToggle />
          </div>

          {/* Desktop auth */}
          <div className="hidden md:block">
            {storedUser !== null ? (
              <div ref={userRef} className="relative">
                <button
                  onClick={() => setUserOpen((prev) => !prev)}
                  className="flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-slate-100 transition-colors"
                >
                  <UserAvatar name={displayName || '?'} />
                  <span className="hidden sm:block text-sm text-slate-700 font-medium max-w-[140px] truncate">
                    {displayName}
                  </span>
                  <svg
                    className={`w-4 h-4 text-slate-400 transition-transform ${userOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {userOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl border border-slate-200 shadow-lg py-1 z-50">
                    {storedUser?.is_admin && (
                      <Link
                        href="/admin"
                        onClick={() => setUserOpen(false)}
                        className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-emerald-700 hover:bg-emerald-50 transition-colors font-medium"
                      >
                        <span>🔧</span> {t('navbar.adminPanel')}
                      </Link>
                    )}
                    <Link
                      href="/dashboard"
                      onClick={() => setUserOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                    >
                      <span>📊</span> {t('navbar.dashboard')}
                    </Link>
                    <Link
                      href="/history"
                      onClick={() => setUserOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                    >
                      <span>📜</span> {t('navbar.history')}
                    </Link>
                    <Link
                      href="/chat"
                      onClick={() => setUserOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                    >
                      <span>💬</span> চ্যাট
                    </Link>
                    <Link
                      href="/pricing"
                      onClick={() => setUserOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                    >
                      <span>⭐</span> {t('pricing.pro')}
                    </Link>
                    <div className="my-1 border-t border-slate-100" />
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <span>🚪</span> {t('navbar.logout')}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  href="/login"
                  className="text-sm text-slate-600 hover:text-slate-900 font-medium px-3 py-2"
                >
                  {t('navbar.login')}
                </Link>
                <Link
                  href="/register"
                  className="text-sm bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-xl transition-colors"
                >
                  {t('navbar.register')}
                </Link>
              </div>
            )}
          </div>

          {/* Mobile: language toggle + mini avatar + hamburger */}
          <div className="flex md:hidden items-center gap-2">
            <LanguageToggle />
            {storedUser !== null && (
              <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
                {(displayName[0] ?? '?').toUpperCase()}
              </div>
            )}
            <button
              onClick={() => setMobileOpen((p) => !p)}
              className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-600 transition-colors"
              aria-label={mobileOpen ? 'মেনু বন্ধ করুন' : 'মেনু খুলুন'}
            >
              {mobileOpen ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>

        </div>
      </div>

      {/* ── Mobile slide-down menu ────────────────────────────────────────── */}
      {mobileOpen && (
        <div className="md:hidden border-t border-slate-100 bg-white shadow-lg">
          <div className="px-4 py-3 space-y-0.5 max-h-[80vh] overflow-y-auto">

            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide px-3 pt-2 pb-1">
              {t('navbar.legalServices')}
            </p>
            {SERVICES_HREFS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={closeMobile}
                className="flex items-center gap-3 px-3 py-2.5 text-sm text-slate-700 hover:bg-slate-50 rounded-xl transition-colors"
              >
                <span className="text-base w-5 text-center">{item.icon}</span>
                {t(`services.${item.key}`)}
              </Link>
            ))}
            <Link
              href="/templates"
              onClick={closeMobile}
              className="flex items-center gap-3 px-3 py-2.5 text-sm text-slate-700 hover:bg-slate-50 rounded-xl transition-colors"
            >
              <span className="text-base w-5 text-center">📝</span>
              দলিল টেমপ্লেট
            </Link>

            <div className="my-1.5 border-t border-slate-100" />

            {MOBILE_LINKS_CONFIG.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={closeMobile}
                className="flex items-center gap-3 px-3 py-2.5 text-sm text-slate-700 hover:bg-slate-50 rounded-xl transition-colors"
              >
                <span className="text-base w-5 text-center">{item.icon}</span>
                {t(item.tKey)}
              </Link>
            ))}

            <div className="my-1.5 border-t border-slate-100" />

            {storedUser !== null ? (
              <>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide px-3 pt-2 pb-1">
                  অ্যাকাউন্ট
                </p>
                {storedUser.is_admin && (
                  <Link
                    href="/admin"
                    onClick={closeMobile}
                    className="flex items-center gap-3 px-3 py-2.5 text-sm text-emerald-700 font-medium hover:bg-emerald-50 rounded-xl transition-colors"
                  >
                    <span className="w-5 text-center">🔧</span> {t('navbar.adminPanel')}
                  </Link>
                )}
                <Link href="/dashboard" onClick={closeMobile} className="flex items-center gap-3 px-3 py-2.5 text-sm text-slate-700 hover:bg-slate-50 rounded-xl transition-colors">
                  <span className="w-5 text-center">📊</span> {t('navbar.dashboard')}
                </Link>
                <Link href="/history" onClick={closeMobile} className="flex items-center gap-3 px-3 py-2.5 text-sm text-slate-700 hover:bg-slate-50 rounded-xl transition-colors">
                  <span className="w-5 text-center">📜</span> {t('navbar.history')}
                </Link>
                <Link href="/chat" onClick={closeMobile} className="flex items-center gap-3 px-3 py-2.5 text-sm text-slate-700 hover:bg-slate-50 rounded-xl transition-colors">
                  <span className="w-5 text-center">💬</span> চ্যাট
                </Link>
                <button
                  onClick={() => { handleLogout(); closeMobile(); }}
                  className="flex items-center gap-3 w-full px-3 py-2.5 text-sm text-red-600 hover:bg-red-50 rounded-xl transition-colors"
                >
                  <span className="w-5 text-center">🚪</span> {t('navbar.logout')}
                </button>
              </>
            ) : (
              <div className="flex gap-2 px-1 pt-2 pb-1">
                <Link
                  href="/login"
                  onClick={closeMobile}
                  className="flex-1 text-center py-2.5 text-sm font-semibold text-slate-700 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors"
                >
                  {t('navbar.login')}
                </Link>
                <Link
                  href="/register"
                  onClick={closeMobile}
                  className="flex-1 text-center py-2.5 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl transition-colors"
                >
                  {t('navbar.register')}
                </Link>
              </div>
            )}

            <div className="pb-2" />
          </div>
        </div>
      )}
    </nav>
  );
}
