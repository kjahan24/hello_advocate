'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

interface CourtCase {
  id:          string;
  case_title:  string;
  case_number: string | null;
  court_name:  string;
  case_type:   string;
  next_date:   string;
  description: string | null;
  status:      string;
  created_at:  string;
  updated_at:  string;
}

interface FormState {
  case_title:  string;
  case_number: string;
  court_name:  string;
  case_type:   string;
  next_date:   string;
  description: string;
  status:      string;
}

const EMPTY_FORM: FormState = {
  case_title:  '',
  case_number: '',
  court_name:  '',
  case_type:   'other',
  next_date:   '',
  description: '',
  status:      'active',
};

// ─── Constants ────────────────────────────────────────────────────────────────

const CASE_TYPES: { value: string; label: string; color: string }[] = [
  { value: 'family',   label: 'পারিবারিক',  color: 'bg-pink-100 text-pink-700' },
  { value: 'land',     label: 'জমি',        color: 'bg-amber-100 text-amber-700' },
  { value: 'business', label: 'ব্যবসায়িক', color: 'bg-blue-100 text-blue-700' },
  { value: 'labor',    label: 'শ্রম',       color: 'bg-orange-100 text-orange-700' },
  { value: 'criminal', label: 'ফৌজদারি',   color: 'bg-red-100 text-red-700' },
  { value: 'other',    label: 'অন্যান্য',   color: 'bg-slate-100 text-slate-600' },
];

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  active:    { label: 'সক্রিয়',   color: 'bg-emerald-100 text-emerald-700' },
  won:       { label: 'জয়',       color: 'bg-green-100 text-green-700' },
  lost:      { label: 'পরাজয়',   color: 'bg-red-100 text-red-700' },
  settled:   { label: 'নিষ্পত্তি', color: 'bg-blue-100 text-blue-700' },
  withdrawn: { label: 'প্রত্যাহার', color: 'bg-slate-100 text-slate-500' },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function daysUntil(dateStr: string): number {
  const today   = new Date(); today.setHours(0, 0, 0, 0);
  const target  = new Date(dateStr); target.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

function formatDateBN(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
}

function caseTypeInfo(value: string) {
  return CASE_TYPES.find((t) => t.value === value) ?? { label: value, color: 'bg-slate-100 text-slate-600' };
}

function todayISO(): string {
  return new Date().toISOString().split('T')[0];
}

// ─── Date urgency badge ───────────────────────────────────────────────────────

function DateBadge({ dateStr, caseStatus }: { dateStr: string; caseStatus: string }) {
  if (caseStatus !== 'active') {
    return <span className="text-xs text-slate-400">{formatDateBN(dateStr)}</span>;
  }
  const days = daysUntil(dateStr);
  if (days < 0) {
    return (
      <span className="flex items-center gap-1 text-xs font-semibold text-slate-400">
        {formatDateBN(dateStr)} <span className="text-slate-300">(অতীত)</span>
      </span>
    );
  }
  if (days === 0) {
    return (
      <span className="flex items-center gap-1 text-xs font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
        🔴 আজ!
      </span>
    );
  }
  if (days <= 7) {
    return (
      <span className="flex items-center gap-1 text-xs font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
        ⚠️ {days} দিন বাকি
      </span>
    );
  }
  if (days <= 30) {
    return (
      <span className="flex items-center gap-1 text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">
        ⏰ {days} দিন বাকি
      </span>
    );
  }
  return <span className="text-xs text-slate-500">{formatDateBN(dateStr)} ({days} দিন)</span>;
}

// ─── Modal ────────────────────────────────────────────────────────────────────

function CaseModal({
  initial,
  onSave,
  onClose,
  saving,
}: {
  initial: FormState;
  onSave:  (f: FormState) => void;
  onClose: () => void;
  saving:  boolean;
}) {
  const [form, setForm] = useState<FormState>(initial);
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setForm((p) => ({ ...p, [k]: v }));

  const inputCls = 'w-full px-3 py-2.5 rounded-xl border border-slate-200 text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500';
  const overlayRef = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="font-bold text-slate-800">
            {initial.case_title ? 'মামলা সম্পাদনা করুন' : 'নতুন মামলা যোগ করুন'}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">✕</button>
        </div>

        <form
          onSubmit={(e) => { e.preventDefault(); onSave(form); }}
          className="px-6 py-5 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">মামলার শিরোনাম *</label>
            <input required value={form.case_title} onChange={(e) => set('case_title', e.target.value)}
              placeholder="যেমন: জমি বিরোধ মামলা" className={inputCls} />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">মামলা নম্বর <span className="text-slate-400 font-normal">(ঐচ্ছিক)</span></label>
            <input value={form.case_number} onChange={(e) => set('case_number', e.target.value)}
              placeholder="Case No. 123/2024" className={inputCls} />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">আদালতের নাম *</label>
            <input required value={form.court_name} onChange={(e) => set('court_name', e.target.value)}
              placeholder="ঢাকা জেলা আদালত" className={inputCls} />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">মামলার ধরন</label>
              <select value={form.case_type} onChange={(e) => set('case_type', e.target.value)} className={inputCls}>
                {CASE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">অবস্থা</label>
              <select value={form.status} onChange={(e) => set('status', e.target.value)} className={inputCls}>
                {Object.entries(STATUS_CONFIG).map(([v, c]) => <option key={v} value={v}>{c.label}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">পরবর্তী তারিখ *</label>
            <input required type="date" min={todayISO()} value={form.next_date}
              onChange={(e) => set('next_date', e.target.value)} className={inputCls} />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">বিবরণ <span className="text-slate-400 font-normal">(ঐচ্ছিক)</span></label>
            <textarea rows={3} value={form.description} onChange={(e) => set('description', e.target.value)}
              placeholder="মামলার সংক্ষিপ্ত বিবরণ..." className={`${inputCls} resize-none`} />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 border border-slate-200 text-slate-600 font-semibold py-2.5 rounded-xl text-sm hover:bg-slate-50 transition-colors">
              বাতিল
            </button>
            <button type="submit" disabled={saving}
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-semibold py-2.5 rounded-xl text-sm transition-colors">
              {saving ? 'সংরক্ষণ হচ্ছে…' : 'সংরক্ষণ করুন'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Case Card ────────────────────────────────────────────────────────────────

function CaseCard({
  c,
  onEdit,
  onDelete,
}: {
  c:        CourtCase;
  onEdit:   (c: CourtCase) => void;
  onDelete: (id: string) => void;
}) {
  const typeInfo = caseTypeInfo(c.case_type);
  const statusCfg = STATUS_CONFIG[c.status] ?? { label: c.status, color: 'bg-slate-100 text-slate-600' };
  const days = daysUntil(c.next_date);
  const urgent = c.status === 'active' && days >= 0 && days <= 7;

  return (
    <div className={`bg-white rounded-2xl border shadow-sm p-5 flex flex-col gap-3 ${urgent ? 'border-red-300' : 'border-slate-200'}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-bold text-slate-800 text-sm leading-snug truncate">{c.case_title}</h3>
          {c.case_number && <p className="text-xs text-slate-400 mt-0.5">{c.case_number}</p>}
        </div>
        <span className={`flex-shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full ${statusCfg.color}`}>
          {statusCfg.label}
        </span>
      </div>

      {/* Meta */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${typeInfo.color}`}>
          {typeInfo.label}
        </span>
        <span className="text-xs text-slate-500">📍 {c.court_name}</span>
      </div>

      {/* Date */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-500 font-medium">পরবর্তী তারিখ:</span>
        <DateBadge dateStr={c.next_date} caseStatus={c.status} />
      </div>

      {c.description && (
        <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">{c.description}</p>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onEdit(c)}
          className="flex-1 text-xs font-semibold text-slate-600 border border-slate-200 hover:bg-slate-50 py-2 rounded-xl transition-colors"
        >
          ✏️ সম্পাদনা
        </button>
        <button
          onClick={() => onDelete(c.id)}
          className="flex-1 text-xs font-semibold text-red-600 border border-red-200 hover:bg-red-50 py-2 rounded-xl transition-colors"
        >
          🗑️ মুছুন
        </button>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CourtCasesPage() {
  const { t } = useLanguage();
  const router = useRouter();

  const [cases,       setCases]       = useState<CourtCase[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState<string | null>(null);
  const [modalOpen,   setModalOpen]   = useState(false);
  const [editTarget,  setEditTarget]  = useState<CourtCase | null>(null);
  const [saving,      setSaving]      = useState(false);
  const [deleteId,    setDeleteId]    = useState<string | null>(null);

  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

  const authHeader = (t: string) => ({ Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' });

  const fetchCases = async (t: string) => {
    const res  = await fetch(`${API_URL}/api/court-cases`, { headers: authHeader(t) });
    const data: unknown = await res.json();
    if (!res.ok) throw new Error('লোড করা যায়নি');
    setCases(data as CourtCase[]);
  };

  useEffect(() => {
    const t = localStorage.getItem('token');
    if (!t) { router.replace('/login?redirect=/court-cases'); return; }
    void fetchCases(t)
      .catch(() => setError('মামলার তালিকা লোড করা যায়নি।'))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  const handleSave = async (form: FormState) => {
    const t = localStorage.getItem('token');
    if (!t) return;
    setSaving(true);
    try {
      const body = {
        case_title:  form.case_title,
        case_number: form.case_number || null,
        court_name:  form.court_name,
        case_type:   form.case_type,
        next_date:   form.next_date,
        description: form.description || null,
        status:      form.status,
      };
      const url    = editTarget ? `${API_URL}/api/court-cases/${editTarget.id}` : `${API_URL}/api/court-cases`;
      const method = editTarget ? 'PUT' : 'POST';
      const res    = await fetch(url, { method, headers: authHeader(t), body: JSON.stringify(body) });
      if (!res.ok) return;
      await fetchCases(t);
      setModalOpen(false);
      setEditTarget(null);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    const t = localStorage.getItem('token');
    if (!t) return;
    setDeleteId(id);
    try {
      await fetch(`${API_URL}/api/court-cases/${id}`, { method: 'DELETE', headers: authHeader(t) });
      setCases((prev) => prev.filter((c) => c.id !== id));
    } finally {
      setDeleteId(null);
    }
  };

  const openAdd  = () => { setEditTarget(null); setModalOpen(true); };
  const openEdit = (c: CourtCase) => { setEditTarget(c); setModalOpen(true); };

  // ── Stats ────────────────────────────────────────────────────────────────────
  const active    = cases.filter((c) => c.status === 'active').length;
  const upcoming  = cases.filter((c) => c.status === 'active' && daysUntil(c.next_date) >= 0 && daysUntil(c.next_date) <= 7).length;
  const completed = cases.filter((c) => ['won', 'lost', 'settled', 'withdrawn'].includes(c.status)).length;
  const upcomingCases = cases.filter((c) => c.status === 'active' && daysUntil(c.next_date) >= 0 && daysUntil(c.next_date) <= 7);

  const modalInitial: FormState = editTarget
    ? {
        case_title:  editTarget.case_title,
        case_number: editTarget.case_number ?? '',
        court_name:  editTarget.court_name,
        case_type:   editTarget.case_type,
        next_date:   editTarget.next_date,
        description: editTarget.description ?? '',
        status:      editTarget.status,
      }
    : EMPTY_FORM;

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

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* Modal */}
      {modalOpen && (
        <CaseModal
          initial={modalInitial}
          onSave={(f) => void handleSave(f)}
          onClose={() => { setModalOpen(false); setEditTarget(null); }}
          saving={saving}
        />
      )}

      {/* Hero */}
      <section
        className="px-4 py-12 text-center"
        style={{ background: 'linear-gradient(135deg, #064e3b 0%, #065f46 60%, #047857 100%)' }}
      >
        <h1 className="text-3xl sm:text-4xl font-bold text-white mb-2">{t('courtCases.title')}</h1>
        <p className="text-emerald-200 text-base max-w-md mx-auto">
          আপনার মামলার গুরুত্বপূর্ণ তারিখ মনে রাখুন
        </p>
      </section>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">

        {/* Upcoming banner */}
        {upcomingCases.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-2xl px-5 py-4 flex items-start gap-3">
            <span className="text-2xl flex-shrink-0">⚠️</span>
            <div>
              <p className="font-bold text-red-700 text-sm">
                {upcomingCases.length}টি মামলার তারিখ আসছে (৭ দিনের মধ্যে)
              </p>
              <ul className="mt-1.5 space-y-0.5">
                {upcomingCases.map((c) => (
                  <li key={c.id} className="text-xs text-red-600">
                    • {c.case_title} — {formatDateBN(c.next_date)} ({daysUntil(c.next_date) === 0 ? 'আজ!' : `${daysUntil(c.next_date)} দিন বাকি`})
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Stats + Add button row */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div className="grid grid-cols-3 gap-3 flex-1">
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm text-center">
              <p className="text-xl font-bold text-slate-800">{active}</p>
              <p className="text-xs text-slate-500 mt-0.5">সক্রিয় মামলা</p>
            </div>
            <div className={`rounded-2xl p-4 shadow-sm text-center border ${upcoming > 0 ? 'bg-red-50 border-red-200' : 'bg-white border-slate-200'}`}>
              <p className={`text-xl font-bold ${upcoming > 0 ? 'text-red-700' : 'text-slate-800'}`}>{upcoming}</p>
              <p className={`text-xs mt-0.5 ${upcoming > 0 ? 'text-red-500' : 'text-slate-500'}`}>আসন্ন তারিখ</p>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm text-center">
              <p className="text-xl font-bold text-slate-800">{completed}</p>
              <p className="text-xs text-slate-500 mt-0.5">সম্পন্ন মামলা</p>
            </div>
          </div>
          <button
            onClick={openAdd}
            className="flex-shrink-0 bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-6 py-3 rounded-xl text-sm transition-colors shadow-sm"
          >
            + {t('courtCases.addCase')}
          </button>
        </div>

        {/* Cases list */}
        {error ? (
          <p className="text-center text-slate-500 py-10">{error}</p>
        ) : cases.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center shadow-sm">
            <p className="text-4xl mb-3">⚖️</p>
            <p className="text-slate-500 mb-4">এখনো কোনো মামলা যোগ করা হয়নি।</p>
            <button
              onClick={openAdd}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-colors"
            >
              প্রথম মামলা যোগ করুন
            </button>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-4">
            {cases.map((c) => (
              <CaseCard
                key={c.id}
                c={c}
                onEdit={openEdit}
                onDelete={(id) => {
                  if (id === deleteId) return;
                  if (confirm('এই মামলাটি মুছে ফেলবেন?')) void handleDelete(id);
                }}
              />
            ))}
          </div>
        )}

        {cases.length > 0 && (
          <div className="text-center pt-2">
            <Link href="/lawyers" className="text-sm text-emerald-600 hover:underline font-medium">
              আইনজীবী খুঁজুন →
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
