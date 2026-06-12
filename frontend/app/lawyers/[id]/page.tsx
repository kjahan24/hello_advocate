'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import NavBar from '@/components/NavBar';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface LawyerDetail {
  id:                   string;
  name:                 string;
  email:                string | null;
  phone:                string | null;
  bar_number:           string | null;
  specializations:      string[];
  experience_years:     number;
  fee_per_consultation: number | null;
  fee_per_hour:         number | null;
  location:             string | null;
  bio:                  string | null;
  rating:               number;
  total_reviews:        number;
  is_verified:          boolean;
  is_available:         boolean;
}

interface ContactInfo {
  phone:   string | null;
  email:   string | null;
  message: string;
}

const SPEC_LABELS: Record<string, string> = {
  family:               'পারিবারিক আইন',
  land_property:        'জমি ও সম্পত্তি',
  commercial_business:  'ব্যবসায়িক আইন',
  labor_employment:     'শ্রম আইন',
  criminal:             'ফৌজদারি আইন',
  consumer_rights:      'ভোক্তা অধিকার',
  civil:                'দেওয়ানি আইন',
  banking_finance:      'ব্যাংকিং ও অর্থ',
  constitutional:       'সাংবিধানিক আইন',
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

function initials(name: string): string {
  return name.trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join('').toUpperCase();
}

export default function LawyerProfilePage() {
  const params   = useParams();
  const lawyerId = params?.id as string | undefined;

  const [lawyer,      setLawyer]      = useState<LawyerDetail | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState<string | null>(null);
  const [contact,     setContact]     = useState<ContactInfo | null>(null);
  const [contacting,  setContacting]  = useState(false);
  const [contactErr,  setContactErr]  = useState<string | null>(null);

  useEffect(() => {
    if (!lawyerId) return;
    void fetch(`${API_URL}/api/lawyers/${lawyerId}`)
      .then(async (res) => {
        const data: unknown = await res.json();
        if (!res.ok || data === null || typeof data !== 'object') {
          setError('আইনজীবীর তথ্য পাওয়া যায়নি।');
          return;
        }
        setLawyer(data as LawyerDetail);
      })
      .catch(() => setError('সার্ভারের সাথে সংযোগ করা যাচ্ছে না।'))
      .finally(() => setLoading(false));
  }, [lawyerId]);

  const handleContact = async () => {
    setContacting(true);
    setContactErr(null);
    const token = localStorage.getItem('token');
    if (!token) {
      setContactErr('যোগাযোগের তথ্য দেখতে লগইন করুন।');
      setContacting(false);
      return;
    }
    try {
      const res  = await fetch(`${API_URL}/api/lawyers/${lawyerId}/contact`, {
        method:  'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data: unknown = await res.json();
      if (!res.ok) {
        setContactErr('যোগাযোগের তথ্য লোড করা যায়নি।');
        return;
      }
      setContact(data as ContactInfo);
    } catch {
      setContactErr('সার্ভারের সাথে সংযোগ করা যাচ্ছে না।');
    } finally {
      setContacting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50">
        <NavBar />
        <div className="flex justify-center items-center h-[calc(100vh-65px)]">
          <div className="w-10 h-10 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error || !lawyer) {
    return (
      <div className="min-h-screen bg-slate-50">
        <NavBar />
        <div className="flex flex-col items-center justify-center h-[calc(100vh-65px)] gap-4">
          <p className="text-slate-500">{error ?? 'তথ্য পাওয়া যায়নি।'}</p>
          <Link href="/lawyers" className="text-emerald-600 text-sm font-medium hover:underline">
            ← আইনজীবীর তালিকায় ফিরুন
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* Hero */}
      <section
        className="px-4 py-12"
        style={{ background: 'linear-gradient(135deg, #064e3b 0%, #065f46 60%, #047857 100%)' }}
      >
        <div className="max-w-3xl mx-auto flex items-center gap-6">
          <div className="w-20 h-20 rounded-full bg-white/20 flex items-center justify-center text-white font-bold text-2xl flex-shrink-0 border-2 border-white/30">
            {initials(lawyer.name)}
          </div>
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-white">{lawyer.name}</h1>
              {lawyer.is_verified && (
                <span className="bg-white/20 text-white text-xs font-semibold px-2.5 py-1 rounded-full">
                  ✓ যাচাইকৃত
                </span>
              )}
              {!lawyer.is_available && (
                <span className="bg-red-500/80 text-white text-xs font-semibold px-2.5 py-1 rounded-full">
                  অনুপলব্ধ
                </span>
              )}
            </div>
            <p className="text-emerald-200 text-sm mt-1">
              📍 {lawyer.location} · {lawyer.experience_years} বছর অভিজ্ঞতা
            </p>
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-amber-300 font-semibold text-sm">⭐ {lawyer.rating.toFixed(1)}</span>
              <span className="text-emerald-300 text-xs">({lawyer.total_reviews} রিভিউ)</span>
            </div>
          </div>
        </div>
      </section>

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">

        {/* Specializations */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h2 className="font-semibold text-slate-800 mb-3">বিশেষজ্ঞতা</h2>
          <div className="flex flex-wrap gap-2">
            {lawyer.specializations.map((s) => (
              <span
                key={s}
                className={`text-sm font-medium px-3 py-1 rounded-full ${SPEC_COLORS[s] ?? 'bg-slate-100 text-slate-600'}`}
              >
                {SPEC_LABELS[s] ?? s}
              </span>
            ))}
          </div>
        </div>

        {/* Bio */}
        {lawyer.bio && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <h2 className="font-semibold text-slate-800 mb-3">পরিচিতি</h2>
            <p className="text-slate-600 text-sm leading-relaxed">{lawyer.bio}</p>
            {lawyer.bar_number && (
              <p className="text-xs text-slate-400 mt-3">বার নম্বর: {lawyer.bar_number}</p>
            )}
          </div>
        )}

        {/* Fee */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h2 className="font-semibold text-slate-800 mb-3">পরামর্শ ফি</h2>
          <div className="flex flex-wrap gap-6">
            {lawyer.fee_per_consultation !== null && (
              <div>
                <p className="text-xs text-slate-400 mb-1">প্রতি পরামর্শ</p>
                <p className="text-xl font-bold text-emerald-700">৳{lawyer.fee_per_consultation.toLocaleString()}</p>
              </div>
            )}
            {lawyer.fee_per_hour !== null && (
              <div>
                <p className="text-xs text-slate-400 mb-1">প্রতি ঘণ্টা</p>
                <p className="text-xl font-bold text-slate-700">৳{lawyer.fee_per_hour.toLocaleString()}</p>
              </div>
            )}
          </div>
        </div>

        {/* Contact */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h2 className="font-semibold text-slate-800 mb-4">যোগাযোগ করুন</h2>

          {contact ? (
            <div className="space-y-3">
              <p className="text-sm text-slate-600">{contact.message}</p>
              {contact.phone && (
                <a
                  href={`tel:${contact.phone}`}
                  className="flex items-center gap-3 p-3 bg-emerald-50 rounded-xl hover:bg-emerald-100 transition-colors"
                >
                  <span className="text-lg">📞</span>
                  <span className="font-semibold text-emerald-700">{contact.phone}</span>
                </a>
              )}
              {contact.email && (
                <a
                  href={`mailto:${contact.email}`}
                  className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <span className="text-lg">✉️</span>
                  <span className="font-semibold text-slate-700">{contact.email}</span>
                </a>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {contactErr && (
                <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-xl px-3 py-2">
                  {contactErr}
                  {contactErr.includes('লগইন') && (
                    <Link href={`/login?redirect=/lawyers/${lawyerId}`} className="underline ml-1 font-semibold">
                      লগইন করুন
                    </Link>
                  )}
                </p>
              )}
              <button
                onClick={() => void handleContact()}
                disabled={contacting || !lawyer.is_available}
                className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-bold py-3 rounded-xl transition-colors"
              >
                {contacting ? 'লোড হচ্ছে…' : !lawyer.is_available ? 'বর্তমানে অনুপলব্ধ' : 'যোগাযোগের তথ্য দেখুন'}
              </button>
              <p className="text-xs text-slate-400 text-center">লগইন করা ব্যবহারকারীরাই যোগাযোগের তথ্য দেখতে পাবেন</p>
            </div>
          )}
        </div>

        {/* Chat CTA */}
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 text-center">
          <p className="text-emerald-800 font-semibold mb-2">আইনজীবীর সাথে কথা বলার আগে AI থেকে প্রাথমিক তথ্য নিন</p>
          <Link
            href="/chat?q=আইনজীবীর সাথে যোগাযোগ করার আগে কী কী বিষয় জানা দরকার?"
            className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-colors"
          >
            💬 চ্যাটে আলোচনা করুন →
          </Link>
        </div>

        <div className="text-center">
          <Link href="/lawyers" className="text-sm text-slate-500 hover:text-slate-700 hover:underline">
            ← সকল আইনজীবীর তালিকায় ফিরুন
          </Link>
        </div>
      </div>

      <footer className="border-t py-6 text-center text-sm text-slate-400 mt-4">
        <p>⚠️ হ্যালো এ্যাডভকেট আইনি পরামর্শ নয় — গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর সাথে যোগাযোগ করুন।</p>
      </footer>
    </div>
  );
}
