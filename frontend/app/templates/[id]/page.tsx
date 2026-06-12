'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import NavBar from '@/components/NavBar';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

interface TemplateField {
  key:         string;
  label:       string;
  placeholder: string | null;
  type:        string;
  required:    boolean;
}

interface TemplateDetail {
  id:          string;
  title:       string;
  title_en:    string | null;
  category:    string;
  description: string | null;
  fields:      TemplateField[];
  is_pro:      boolean;
  usage_count: number;
}

interface GenerateResponse {
  document_id: string;
  content:     string;
  title:       string;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TemplateFormPage() {
  const params  = useParams<{ id: string }>();
  const router  = useRouter();

  const [template,   setTemplate]   = useState<TemplateDetail | null>(null);
  const [values,     setValues]     = useState<Record<string, string>>({});
  const [loading,    setLoading]    = useState(true);
  const [generating, setGenerating] = useState(false);
  const [result,     setResult]     = useState<GenerateResponse | null>(null);
  const [error,      setError]      = useState('');
  const [copied,     setCopied]     = useState(false);
  const [downloading,setDownloading]= useState(false);
  const [userPlan,   setUserPlan]   = useState<string>('free');
  const resultRef = useRef<HTMLDivElement>(null);

  // Read user plan from localStorage
  useEffect(() => {
    const raw = localStorage.getItem('user');
    if (raw) {
      try {
        const u = JSON.parse(raw) as { plan?: string };
        setUserPlan(u.plan ?? 'free');
      } catch { /* ignore */ }
    }
  }, []);

  // Fetch template details
  useEffect(() => {
    if (!params.id) return;
    fetch(`${API}/api/templates/${params.id}`)
      .then(r => {
        if (!r.ok) throw new Error('not found');
        return r.json();
      })
      .then(data => {
        setTemplate(data as TemplateDetail);
        const initial: Record<string, string> = {};
        (data as TemplateDetail).fields.forEach((f: TemplateField) => { initial[f.key] = ''; });
        setValues(initial);
      })
      .catch(() => setError('টেমপ্লেট লোড করা যায়নি।'))
      .finally(() => setLoading(false));
  }, [params.id]);

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!template) return;

    const token = localStorage.getItem('token');
    if (!token) {
      router.push(`/login?redirect=/templates/${params.id}`);
      return;
    }

    const missing = template.fields.filter(f => f.required && !values[f.key]?.trim());
    if (missing.length > 0) {
      setError(`এই তথ্যগুলি পূরণ করুন: ${missing.map(f => f.label).join(', ')}`);
      return;
    }

    setGenerating(true);
    setError('');
    setResult(null);

    try {
      const res = await fetch(`${API}/api/templates/${params.id}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ field_values: values }),
      });

      if (res.status === 403) {
        const data = await res.json() as { detail: string };
        setError(data.detail ?? 'প্রো প্ল্যান প্রয়োজন।');
        return;
      }
      if (res.status === 429) {
        setError('আজকের প্রশ্নের সীমা শেষ হয়ে গেছে। আগামীকাল আবার চেষ্টা করুন।');
        return;
      }
      if (!res.ok) throw new Error('generation failed');

      const data = await res.json() as GenerateResponse;
      setResult(data);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch {
      setError('দলিল তৈরিতে সমস্যা হয়েছে। পরে আবার চেষ্টা করুন।');
    } finally {
      setGenerating(false);
    }
  }

  async function handleCopy() {
    if (!result) return;
    await navigator.clipboard.writeText(result.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleDownloadPDF() {
    if (!result) return;
    const token = localStorage.getItem('token');
    if (!token) return;

    setDownloading(true);
    try {
      const res = await fetch(`${API}/api/templates/documents/${result.document_id}/pdf`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('pdf failed');

      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `${result.title}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('PDF ডাউনলোডে সমস্যা হয়েছে।');
    } finally {
      setDownloading(false);
    }
  }

  const isPro = userPlan === 'pro' || userPlan === 'lawyer';
  const proBlocked = template?.is_pro && !isPro;

  // ── Loading ────────────────────────────────────────────────────────────────
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

  if (!template || (error && !template)) {
    return (
      <div className="min-h-screen bg-slate-50">
        <NavBar />
        <div className="flex flex-col items-center justify-center h-[calc(100vh-65px)] gap-4">
          <p className="text-slate-500 text-sm">টেমপ্লেট পাওয়া যায়নি।</p>
          <Link href="/templates" className="text-emerald-600 text-sm hover:underline">← সব টেমপ্লেট দেখুন</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* ── Header ───────────────────────────────────────────────────────────── */}
      <section
        className="px-4 py-10"
        style={{ background: 'linear-gradient(135deg, #064e3b 0%, #065f46 60%, #047857 100%)' }}
      >
        <div className="max-w-3xl mx-auto">
          <Link
            href="/templates"
            className="inline-flex items-center gap-1.5 text-emerald-200 text-sm mb-5 hover:text-white transition-colors"
          >
            ← সব টেমপ্লেট
          </Link>
          <div className="flex items-start gap-4">
            <div>
              <div className="flex items-center gap-3 flex-wrap mb-2">
                <h1 className="text-2xl sm:text-3xl font-bold text-white">{template.title}</h1>
                {template.is_pro && (
                  <span className="px-2.5 py-0.5 bg-amber-400 text-amber-900 text-xs font-bold rounded-full">PRO</span>
                )}
              </div>
              {template.title_en && (
                <p className="text-emerald-300 text-sm mb-2">{template.title_en}</p>
              )}
              {template.description && (
                <p className="text-emerald-100 text-sm leading-relaxed">{template.description}</p>
              )}
            </div>
          </div>
        </div>
      </section>

      <div className="max-w-3xl mx-auto px-4 py-8">

        {/* ── PRO gate ─────────────────────────────────────────────────────── */}
        {proBlocked && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 mb-6 flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex-1">
              <p className="font-semibold text-amber-800 mb-1">⭐ এটি একটি প্রো টেমপ্লেট</p>
              <p className="text-sm text-amber-700">এই দলিলটি তৈরি করতে প্রো সদস্যপদ প্রয়োজন।</p>
            </div>
            <Link
              href="/pricing"
              className="flex-shrink-0 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold rounded-xl transition-colors"
            >
              প্রো-তে আপগ্রেড করুন →
            </Link>
          </div>
        )}

        {/* ── Form ─────────────────────────────────────────────────────────── */}
        <form onSubmit={handleGenerate} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
          <h2 className="text-base font-semibold text-slate-800 mb-5">
            প্রয়োজনীয় তথ্য পূরণ করুন
          </h2>

          <div className="space-y-4">
            {template.fields.map(field => (
              <div key={field.key}>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-0.5">*</span>}
                </label>
                {field.type === 'textarea' ? (
                  <textarea
                    value={values[field.key] ?? ''}
                    onChange={e => setValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                    placeholder={field.placeholder ?? ''}
                    rows={3}
                    className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent resize-none"
                    disabled={proBlocked}
                  />
                ) : (
                  <input
                    type="text"
                    value={values[field.key] ?? ''}
                    onChange={e => setValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                    placeholder={field.placeholder ?? ''}
                    className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent"
                    disabled={proBlocked}
                  />
                )}
              </div>
            ))}
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
              {error}
            </div>
          )}

          <div className="mt-6">
            {proBlocked ? (
              <Link
                href="/pricing"
                className="block w-full text-center py-3 bg-amber-500 hover:bg-amber-600 text-white font-semibold rounded-xl transition-colors"
              >
                ⭐ প্রো সদস্যপদ নিন
              </Link>
            ) : (
              <button
                type="submit"
                disabled={generating}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {generating ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    দলিল তৈরি হচ্ছে... অপেক্ষা করুন
                  </>
                ) : (
                  '✨ AI দিয়ে তৈরি করুন'
                )}
              </button>
            )}
          </div>
        </form>

        {/* ── Result ───────────────────────────────────────────────────────── */}
        {result && (
          <div ref={resultRef} className="bg-white rounded-2xl border border-emerald-200 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 bg-emerald-50 border-b border-emerald-200">
              <div className="flex items-center gap-2">
                <span className="text-emerald-600 text-lg">✅</span>
                <span className="font-semibold text-emerald-800">{result.title} — তৈরি হয়েছে</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded-lg hover:border-slate-300 transition-colors"
                >
                  {copied ? '✓ কপি হয়েছে' : '📋 কপি করুন'}
                </button>
                <button
                  onClick={handleDownloadPDF}
                  disabled={downloading}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors disabled:opacity-60"
                >
                  {downloading ? '...' : '📥 PDF ডাউনলোড'}
                </button>
              </div>
            </div>

            <div className="p-6">
              <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 leading-relaxed">
                {result.content}
              </pre>
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
              <p className="text-xs text-slate-400">
                ⚠️ এটি AI-তৈরি খসড়া। চূড়ান্ত করার আগে আইনজীবীর পরামর্শ নিন।
              </p>
              <button
                onClick={() => setResult(null)}
                className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors"
              >
                🔄 আবার তৈরি করুন
              </button>
            </div>
          </div>
        )}

        {/* ── Lawyer CTA ───────────────────────────────────────────────────── */}
        <div className="mt-6 bg-emerald-50 border border-emerald-200 rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex-1">
            <p className="font-semibold text-emerald-800 text-sm mb-1">⚖️ বিশেষজ্ঞ আইনজীবীর সাহায্য নিন</p>
            <p className="text-xs text-emerald-700">গুরুত্বপূর্ণ দলিলের জন্য একজন অভিজ্ঞ আইনজীবীর সাথে পরামর্শ করুন।</p>
          </div>
          <Link
            href="/lawyers"
            className="flex-shrink-0 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-xl transition-colors"
          >
            আইনজীবী খুঁজুন →
          </Link>
        </div>
      </div>

      <footer className="border-t py-6 text-center text-sm text-slate-400 mt-4">
        <p>⚠️ হ্যালো এ্যাডভকেট আইনি পরামর্শ নয় — গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর সাথে যোগাযোগ করুন।</p>
      </footer>
    </div>
  );
}
