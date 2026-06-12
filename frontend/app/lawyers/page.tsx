'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Lawyer {
  id:                   string;
  name:                 string;
  specializations:      string[];
  experience_years:     number;
  fee_per_consultation: number | null;
  fee_per_hour:         number | null;
  location:             string | null;
  rating:               number;
  total_reviews:        number;
  is_verified:          boolean;
  is_available:         boolean;
  bio:                  string | null;
  bar_number:           string | null;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SPECIALIZATION_OPTIONS = [
  { value: '',                  label: 'সব বিভাগ' },
  { value: 'family',            label: 'পারিবারিক আইন' },
  { value: 'land_property',     label: 'জমি ও সম্পত্তি' },
  { value: 'commercial_business', label: 'ব্যবসায়িক আইন' },
  { value: 'labor_employment',  label: 'শ্রম আইন' },
  { value: 'criminal',          label: 'ফৌজদারি আইন' },
  { value: 'consumer_rights',   label: 'ভোক্তা অধিকার' },
  { value: 'civil',             label: 'দেওয়ানি আইন' },
  { value: 'banking_finance',   label: 'ব্যাংকিং ও অর্থ' },
];

const LOCATION_OPTIONS = [
  { value: '',          label: 'সব জেলা' },
  { value: 'ঢাকা',      label: 'ঢাকা' },
  { value: 'চট্টগ্রাম', label: 'চট্টগ্রাম' },
  { value: 'সিলেট',    label: 'সিলেট' },
  { value: 'রাজশাহী',  label: 'রাজশাহী' },
  { value: 'খুলনা',    label: 'খুলনা' },
  { value: 'বরিশাল',   label: 'বরিশাল' },
];

const SPEC_LABELS: Record<string, string> = {
  family:               'পারিবারিক',
  land_property:        'জমি',
  commercial_business:  'ব্যবসায়িক',
  labor_employment:     'শ্রম',
  criminal:             'ফৌজদারি',
  consumer_rights:      'ভোক্তা',
  civil:                'দেওয়ানি',
  banking_finance:      'ব্যাংকিং',
  constitutional:       'সাংবিধানিক',
};

const SPEC_COLORS: Record<string, string> = {
  family:              'bg-pink-100 text-pink-700',
  land_property:       'bg-amber-100 text-amber-700',
  commercial_business: 'bg-blue-100 text-blue-700',
  labor_employment:    'bg-orange-100 text-orange-700',
  criminal:            'bg-red-100 text-red-700',
  consumer_rights:     'bg-purple-100 text-purple-700',
  civil:               'bg-slate-100 text-slate-600',
  banking_finance:     'bg-teal-100 text-teal-700',
  constitutional:      'bg-indigo-100 text-indigo-700',
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

function Stars({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-1 text-sm font-semibold text-amber-600">
      ⭐ {rating.toFixed(1)}
    </span>
  );
}

// ─── Card ─────────────────────────────────────────────────────────────────────

function LawyerCard({ lawyer }: { lawyer: Lawyer }) {
  const { t } = useLanguage();
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col gap-4 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 font-bold text-lg flex-shrink-0">
          {initials(lawyer.name)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-bold text-slate-800 text-sm leading-tight">{lawyer.name}</h3>
            {lawyer.is_verified && (
              <span className="bg-emerald-100 text-emerald-700 text-xs font-semibold px-2 py-0.5 rounded-full flex-shrink-0">
                ✓ যাচাইকৃত
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            📍 {lawyer.location ?? '—'} · {lawyer.experience_years} বছর অভিজ্ঞতা
          </p>
        </div>
      </div>

      {/* Specialization tags */}
      <div className="flex flex-wrap gap-1.5">
        {lawyer.specializations.slice(0, 3).map((s) => (
          <span
            key={s}
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${SPEC_COLORS[s] ?? 'bg-slate-100 text-slate-600'}`}
          >
            {SPEC_LABELS[s] ?? s}
          </span>
        ))}
      </div>

      {/* Rating + fee */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-3">
          <Stars rating={lawyer.rating} />
          <span className="text-slate-400 text-xs">({lawyer.total_reviews} রিভিউ)</span>
        </div>
        {lawyer.fee_per_consultation !== null && (
          <span className="text-emerald-700 font-semibold text-xs bg-emerald-50 px-2.5 py-1 rounded-full">
            পরামর্শ ৳{lawyer.fee_per_consultation.toLocaleString()}
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <Link
          href={`/lawyers/${lawyer.id}`}
          className="flex-1 text-center text-sm font-semibold text-slate-700 border border-slate-200 hover:bg-slate-50 px-3 py-2 rounded-xl transition-colors"
        >
          {t('lawyers.viewProfile')}
        </Link>
        <Link
          href={`/lawyers/${lawyer.id}`}
          className="flex-1 text-center text-sm font-semibold bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 rounded-xl transition-colors"
        >
          {t('lawyers.contact')}
        </Link>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LawyersPage() {
  const { t } = useLanguage();
  const [lawyers,        setLawyers]        = useState<Lawyer[]>([]);
  const [loading,        setLoading]        = useState(true);
  const [error,          setError]          = useState<string | null>(null);
  const [specialization, setSpecialization] = useState('');
  const [location,       setLocation]       = useState('');

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (specialization) params.set('specialization', specialization);
    if (location)       params.set('location', location);

    void fetch(`${API_URL}/api/lawyers?${params.toString()}`)
      .then(async (res) => {
        const data: unknown = await res.json();
        if (!res.ok) { setError('আইনজীবীর তালিকা লোড করা যায়নি।'); return; }
        setLawyers(data as Lawyer[]);
      })
      .catch(() => setError('সার্ভারের সাথে সংযোগ করা যাচ্ছে না।'))
      .finally(() => setLoading(false));
  }, [specialization, location]);

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* Hero */}
      <section
        className="px-4 py-14 text-center"
        style={{ background: 'linear-gradient(135deg, #064e3b 0%, #065f46 60%, #047857 100%)' }}
      >
        <h1 className="text-3xl sm:text-5xl font-bold text-white mb-3">{t('lawyers.title')}</h1>
        <p className="text-emerald-100 text-lg max-w-xl mx-auto">
          অভিজ্ঞ ও যাচাইকৃত আইনজীবীদের সাথে সরাসরি যোগাযোগ করুন।
        </p>
      </section>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Filter bar */}
        <div className="flex flex-col sm:flex-row gap-3 mb-8">
          <select
            value={specialization}
            onChange={(e) => setSpecialization(e.target.value)}
            className="flex-1 sm:max-w-xs px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {SPECIALIZATION_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          <select
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="flex-1 sm:max-w-xs px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {LOCATION_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          {(specialization || location) && (
            <button
              onClick={() => { setSpecialization(''); setLocation(''); }}
              className="text-sm text-slate-500 hover:text-slate-700 px-3 py-2 rounded-xl border border-slate-200 bg-white transition-colors"
            >
              ফিল্টার মুছুন ✕
            </button>
          )}
        </div>

        {/* Results */}
        {loading ? (
          <div className="flex justify-center py-24">
            <div className="w-10 h-10 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <p className="text-center text-slate-500 py-20">{error}</p>
        ) : lawyers.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-slate-400 text-lg mb-2">কোনো আইনজীবী পাওয়া যায়নি।</p>
            <button
              onClick={() => { setSpecialization(''); setLocation(''); }}
              className="text-emerald-600 text-sm font-medium hover:underline"
            >
              সব ফিল্টার মুছুন
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm text-slate-500 mb-4">{lawyers.length}জন আইনজীবী পাওয়া গেছে</p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {lawyers.map((l) => (
                <LawyerCard key={l.id} lawyer={l} />
              ))}
            </div>
          </>
        )}
      </div>

      <footer className="border-t py-6 text-center text-sm text-slate-400 mt-8">
        <p>⚠️ হ্যালো এ্যাডভকেট আইনি পরামর্শ নয় — গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর সাথে যোগাযোগ করুন।</p>
      </footer>
    </div>
  );
}
