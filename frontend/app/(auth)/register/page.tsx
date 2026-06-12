'use client';

import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { authRegister } from '@/lib/api';
import { useLanguage } from '@/contexts/LanguageContext';

interface FormState {
  name:            string;
  email:           string;
  phone:           string;
  password:        string;
  confirmPassword: string;
  terms:           boolean;
}

export default function RegisterPage() {
  const { t } = useLanguage();
  const router = useRouter();

  const [form, setForm] = useState<FormState>({
    name:            '',
    email:           '',
    phone:           '',
    password:        '',
    confirmPassword: '',
    terms:           false,
  });
  const [error,   setError]   = useState('');
  const [loading, setLoading] = useState(false);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirmPassword) {
      setError(t('auth.passwordMismatch'));
      return;
    }
    if (!form.terms) {
      setError(t('auth.termsRequired'));
      return;
    }

    setLoading(true);
    try {
      const data = await authRegister({
        name:     form.name,
        email:    form.email,
        password: form.password,
        phone:    form.phone || null,
      });

      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      router.push('/chat');
    } catch (err: unknown) {
      const detail =
        err !== null &&
        typeof err === 'object' &&
        'response' in err &&
        err.response !== null &&
        typeof err.response === 'object' &&
        'data' in err.response &&
        err.response.data !== null &&
        typeof err.response.data === 'object' &&
        'detail' in err.response.data &&
        typeof (err.response.data as Record<string, unknown>).detail === 'string'
          ? (err.response.data as Record<string, string>).detail
          : null;
      setError(detail ?? t('auth.connectionError'));
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    'w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm transition-all';

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50 to-white flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/">
            <div className="w-14 h-14 rounded-2xl bg-emerald-600 flex items-center justify-center shadow-lg mx-auto mb-3">
              <span className="text-white font-bold text-2xl">আ</span>
            </div>
          </Link>
          <h1 className="text-2xl font-bold text-slate-800">হ্যালো এ্যাডভকেট</h1>
          <p className="text-slate-500 text-sm mt-1">{t('auth.registerTitle')}</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8">
          {error && (
            <div className="mb-5 px-4 py-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">
              {error}
            </div>
          )}

          <form onSubmit={(e) => { void handleSubmit(e); }} className="space-y-4">

            {/* Full name */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                {t('auth.name')}
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                required
                autoComplete="name"
                placeholder={t('auth.namePlaceholder')}
                className={inputClass}
              />
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                {t('auth.email')}
              </label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => set('email', e.target.value)}
                required
                autoComplete="email"
                placeholder={t('auth.emailPlaceholder')}
                className={inputClass}
              />
            </div>

            {/* Phone (optional) */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                {t('auth.phone')}
              </label>
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => set('phone', e.target.value)}
                autoComplete="tel"
                placeholder="+880 1X-XXXXXXXX"
                className={inputClass}
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                {t('auth.password')}
              </label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => set('password', e.target.value)}
                required
                minLength={6}
                autoComplete="new-password"
                placeholder={t('auth.passwordHint')}
                className={inputClass}
              />
            </div>

            {/* Confirm password */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                {t('auth.confirmPassword')}
              </label>
              <input
                type="password"
                value={form.confirmPassword}
                onChange={(e) => set('confirmPassword', e.target.value)}
                required
                autoComplete="new-password"
                placeholder={t('auth.confirmPasswordPlaceholder')}
                className={inputClass}
              />
            </div>

            {/* Terms checkbox */}
            <label className="flex items-start gap-2.5 cursor-pointer select-none pt-1">
              <input
                type="checkbox"
                checked={form.terms}
                onChange={(e) => set('terms', e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 mt-0.5 flex-shrink-0"
              />
              <span className="text-sm text-slate-600 leading-relaxed">
                {t('auth.agreeTerms')}
              </span>
            </label>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-semibold py-3 rounded-xl transition-colors text-sm shadow-sm mt-2"
            >
              {loading ? t('auth.registering') : t('auth.registerBtn')}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-6">
            {t('auth.hasAccount')}{' '}
            <Link
              href="/login"
              className="text-emerald-600 hover:text-emerald-700 font-semibold"
            >
              {t('auth.login')}
            </Link>
          </p>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          {t('auth.aiDisclaimer')}
        </p>
      </div>
    </div>
  );
}
