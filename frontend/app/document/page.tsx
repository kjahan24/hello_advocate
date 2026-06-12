'use client';

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';
import { analyzeImage, type ImageAnalysisResult } from '@/lib/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AnalysisResult {
  summary: string;
  risks:   string[];
  dates:   string[];
  advice:  string;
}

type ActiveTab = 'document' | 'image';

// ─── Constants ────────────────────────────────────────────────────────────────

const ALLOWED_DOC_EXTS  = ['.pdf', '.doc', '.docx'];
const ALLOWED_IMG_EXTS  = ['.jpg', '.jpeg', '.png', '.webp', '.gif'];
const MAX_DOC_BYTES     = 10 * 1024 * 1024;
const MAX_IMG_BYTES     =  5 * 1024 * 1024;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validateDoc(f: File): string | null {
  const ext = '.' + (f.name.split('.').pop() ?? '').toLowerCase();
  if (!ALLOWED_DOC_EXTS.includes(ext)) return 'সমর্থিত ফরম্যাট: PDF, DOC, DOCX';
  if (f.size > MAX_DOC_BYTES) return 'ফাইলের আকার সর্বোচ্চ ১০ MB হতে পারে।';
  return null;
}

function validateImg(f: File): string | null {
  const ext = '.' + (f.name.split('.').pop() ?? '').toLowerCase();
  if (!ALLOWED_IMG_EXTS.includes(ext)) return 'সমর্থিত ফরম্যাট: JPG, PNG, WEBP';
  if (f.size > MAX_IMG_BYTES) return 'ছবির সাইজ সর্বোচ্চ ৫ MB হতে পারে।';
  return null;
}

// ─── Markdown renderer ────────────────────────────────────────────────────────

function MarkdownContent({ text }: { text: string }) {
  const lines = text.split('\n');
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        if (line.startsWith('## ')) {
          return (
            <h3 key={i} className="font-bold text-slate-800 text-base mt-5 mb-1.5 first:mt-0 flex items-center gap-1.5">
              {line.slice(3)}
            </h3>
          );
        }
        if (line.startsWith('# ')) {
          return <h2 key={i} className="font-bold text-slate-900 text-lg mt-4 mb-2 first:mt-0">{line.slice(2)}</h2>;
        }
        if (line.trim() === '') {
          return <div key={i} className="h-1.5" />;
        }
        const parts = line.split(/(\*\*.*?\*\*)/g);
        return (
          <p key={i} className="text-slate-700 text-sm leading-relaxed">
            {parts.map((part, j) =>
              part.startsWith('**') && part.endsWith('**')
                ? <strong key={j}>{part.slice(2, -2)}</strong>
                : part
            )}
          </p>
        );
      })}
    </div>
  );
}

// ─── Document type badge ──────────────────────────────────────────────────────

const DOC_TYPE_CONFIG: Record<string, { color: string; labelBn: string; labelEn: string }> = {
  court_notice: { color: 'bg-red-100 text-red-700 border-red-200',     labelBn: '⚖️ আদালত নোটিশ',  labelEn: '⚖️ Court Notice' },
  contract:     { color: 'bg-blue-100 text-blue-700 border-blue-200',  labelBn: '📝 চুক্তিপত্র',    labelEn: '📝 Contract' },
  land_deed:    { color: 'bg-green-100 text-green-700 border-green-200',labelBn: '🏠 জমির দলিল',     labelEn: '🏠 Land Deed' },
  legal_form:   { color: 'bg-purple-100 text-purple-700 border-purple-200', labelBn: '📋 আইনি ফর্ম', labelEn: '📋 Legal Form' },
  id_document:  { color: 'bg-orange-100 text-orange-700 border-orange-200', labelBn: '🪪 পরিচয়পত্র', labelEn: '🪪 ID Document' },
  other:        { color: 'bg-slate-100 text-slate-600 border-slate-200',labelBn: '📄 অন্যান্য',     labelEn: '📄 Other' },
};

function DocTypeBadge({ type, lang }: { type: string; lang: string }) {
  const cfg = DOC_TYPE_CONFIG[type] ?? DOC_TYPE_CONFIG.other;
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${cfg.color}`}>
      {lang === 'en' ? cfg.labelEn : cfg.labelBn}
    </span>
  );
}

// ─── Document tab — upload area ───────────────────────────────────────────────

function DocUploadArea({
  file, isDragging, isLoading, error,
  onDragOver, onDragLeave, onDrop, onFileChange, onClear, onAnalyze,
}: {
  file:       File | null;
  isDragging: boolean;
  isLoading:  boolean;
  error:      string | null;
  onDragOver:   (e: DragEvent<HTMLDivElement>) => void;
  onDragLeave:  () => void;
  onDrop:       (e: DragEvent<HTMLDivElement>) => void;
  onFileChange: (e: ChangeEvent<HTMLInputElement>) => void;
  onClear:    () => void;
  onAnalyze:  () => void;
}) {
  const { t } = useLanguage();
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => !file && inputRef.current?.click()}
      className={`border-2 border-dashed rounded-2xl p-6 sm:p-10 text-center transition-colors ${
        file ? 'cursor-default' : 'cursor-pointer'
      } ${
        isDragging
          ? 'border-emerald-500 bg-emerald-50'
          : 'border-slate-300 bg-white hover:border-emerald-400 hover:bg-emerald-50/30'
      }`}
    >
      <input ref={inputRef} type="file" accept=".pdf,.doc,.docx" className="hidden" onChange={onFileChange} />

      {!file ? (
        <>
          <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <p className="text-slate-700 font-semibold text-base mb-1">{t('document.uploadText')}</p>
          <p className="text-slate-400 text-sm mb-4">অথবা</p>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
            className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-colors"
          >
            {t('document.chooseFile')}
          </button>
          <p className="text-xs text-slate-400 mt-4">PDF, DOC, DOCX · সর্বোচ্চ ১০ MB</p>
        </>
      ) : (
        <div onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center flex-shrink-0">
              <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div className="text-left">
              <p className="font-semibold text-slate-800 text-sm">{file.name}</p>
              <p className="text-xs text-slate-400">{formatSize(file.size)}</p>
            </div>
            <button type="button" onClick={onClear} className="ml-2 text-slate-400 hover:text-red-500 transition-colors text-lg leading-none" aria-label="ফাইল সরান">
              ✕
            </button>
          </div>
          {error && <p className="text-red-600 text-sm mb-4">{error}</p>}
          <button
            type="button"
            onClick={onAnalyze}
            disabled={isLoading}
            className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-bold px-8 py-3 rounded-xl text-base transition-colors shadow-md"
          >
            {isLoading ? (
              <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />{t('document.analyzing')}</>
            ) : (
              t('document.analyze')
            )}
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Document tab — result section ────────────────────────────────────────────

function DocResultSection({
  result, filename, pdfLoading, onReset, onDownloadPdf,
}: {
  result:        AnalysisResult;
  filename:      string;
  pdfLoading:    boolean;
  onReset:       () => void;
  onDownloadPdf: () => void;
}) {
  const { t } = useLanguage();
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xl font-bold text-slate-800">বিশ্লেষণের ফলাফল</h2>
        <button onClick={onReset} className="text-sm text-slate-500 hover:text-slate-800 underline transition-colors">
          নতুন ডকুমেন্ট
        </button>
      </div>
      {filename && <p className="text-xs text-slate-400 -mt-2">📄 {filename}</p>}

      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <h3 className="font-bold text-slate-800 text-base mb-3">📋 {t('document.summary')}</h3>
        <p className="text-slate-700 text-sm leading-relaxed">{result.summary}</p>
      </div>

      <div className="bg-red-50 border border-red-200 rounded-2xl p-6 shadow-sm">
        <h3 className="font-bold text-red-800 text-base mb-3">⚠️ {t('document.risks')}</h3>
        {result.risks.length > 0 ? (
          <ul className="space-y-2">
            {result.risks.map((risk, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-red-700">
                <span className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full bg-red-200 text-red-700 font-bold text-xs flex items-center justify-center">{i + 1}</span>
                {risk}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-red-600">কোনো উল্লেখযোগ্য ঝুঁকি পাওয়া যায়নি।</p>
        )}
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6 shadow-sm">
        <h3 className="font-bold text-blue-800 text-base mb-3">📅 {t('document.dates')}</h3>
        {result.dates.length > 0 ? (
          <ul className="space-y-2">
            {result.dates.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-blue-700">
                <span className="mt-0.5 flex-shrink-0 text-blue-400">•</span>
                {d}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-blue-600">কোনো নির্দিষ্ট তারিখ বা শর্ত পাওয়া যায়নি।</p>
        )}
      </div>

      <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 shadow-sm">
        <h3 className="font-bold text-emerald-800 text-base mb-3">💡 {t('document.advice')}</h3>
        <p className="text-slate-700 text-sm leading-relaxed">{result.advice}</p>
      </div>

      <div className="flex justify-center pt-2">
        <button
          onClick={onDownloadPdf}
          disabled={pdfLoading}
          className="inline-flex items-center gap-2 border-2 border-emerald-600 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50 disabled:cursor-not-allowed font-semibold px-6 py-3 rounded-xl text-sm transition-colors"
        >
          {pdfLoading ? (
            <><span className="w-4 h-4 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />রিপোর্ট তৈরি হচ্ছে...</>
          ) : (
            '📥 PDF রিপোর্ট ডাউনলোড করুন'
          )}
        </button>
      </div>

      <div className="text-center pt-4 pb-2 flex flex-col sm:flex-row items-center justify-center gap-3">
        <Link href="/lawyers" className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-8 py-4 rounded-xl text-base transition-colors shadow-md hover:shadow-lg">
          ⚖️ বিশেষজ্ঞ আইনজীবীর সাথে কথা বলুন →
        </Link>
        <Link href="/chat" className="inline-flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold px-6 py-4 rounded-xl text-base transition-colors border border-slate-200 shadow-sm">
          💬 AI-এ আরও প্রশ্ন করুন
        </Link>
      </div>
    </div>
  );
}

// ─── Vision tab ────────────────────────────────────────────────────────────────

function VisionTab() {
  const { t, language } = useLanguage();
  const inputRef = useRef<HTMLInputElement>(null);

  const [imgFile,    setImgFile]    = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result,     setResult]     = useState<ImageAnalysisResult | null>(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState<string | null>(null);
  const [dragging,   setDragging]   = useState(false);
  const [copied,     setCopied]     = useState(false);

  useEffect(() => {
    return () => { if (previewUrl) URL.revokeObjectURL(previewUrl); };
  }, [previewUrl]);

  function pickImage(file: File) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setImgFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setError(null);
    setResult(null);
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>) { e.preventDefault(); setDragging(true); }
  function handleDragLeave() { setDragging(false); }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (!f) return;
    const err = validateImg(f);
    if (err) { setError(err); return; }
    pickImage(f);
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const err = validateImg(f);
    if (err) { setError(err); return; }
    pickImage(f);
    e.target.value = '';
  }

  async function handleAnalyze() {
    if (!imgFile) return;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeImage(imgFile, language);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'বিশ্লেষণ ব্যর্থ হয়েছে।');
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setImgFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
  }

  async function handleCopy() {
    if (!result) return;
    await navigator.clipboard.writeText(result.analysis);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // ── No file selected: upload zone ────────────────────────────────────────────
  if (!imgFile) {
    return (
      <>
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-6 sm:p-10 text-center cursor-pointer transition-colors ${
            dragging
              ? 'border-emerald-500 bg-emerald-50'
              : 'border-slate-300 bg-white hover:border-emerald-400 hover:bg-emerald-50/30'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="hidden"
            onChange={handleFileChange}
          />
          <div className="w-16 h-16 bg-violet-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <p className="text-slate-700 font-semibold text-base mb-1">{t('document.imageUploadText')}</p>
          <p className="text-xs text-slate-400 mt-3">{t('document.imageFormats')}</p>
        </div>
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>
        )}
      </>
    );
  }

  // ── File selected, not yet analyzed ──────────────────────────────────────────
  if (!result) {
    return (
      <div className="space-y-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          {/* Preview */}
          <div className="flex flex-col sm:flex-row items-start gap-5">
            <div className={`relative rounded-xl overflow-hidden border border-slate-200 flex-shrink-0 ${loading ? 'animate-pulse' : ''}`}>
              {previewUrl && (
                <img
                  src={previewUrl}
                  alt="Preview"
                  className="max-h-72 max-w-full sm:max-w-xs object-contain"
                />
              )}
            </div>
            <div className="flex-1">
              <p className="font-semibold text-slate-800 text-sm mb-1">{imgFile.name}</p>
              <p className="text-xs text-slate-400 mb-4">{formatSize(imgFile.size)}</p>
              <button
                type="button"
                onClick={handleReset}
                className="text-sm text-slate-500 hover:text-red-500 underline transition-colors"
              >
                {t('document.changeImage')}
              </button>
            </div>
          </div>

          {error && <p className="text-red-600 text-sm mt-4">{error}</p>}

          <div className="mt-6 flex justify-center">
            <button
              type="button"
              onClick={() => { void handleAnalyze(); }}
              disabled={loading}
              className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-bold px-8 py-3 rounded-xl text-base transition-colors shadow-md"
            >
              {loading ? (
                <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />{t('document.analyzingImage')}</>
              ) : (
                t('document.analyzeImage')
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Result ────────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-5">
      {/* Header row */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <h2 className="text-xl font-bold text-slate-800">
            {language === 'en' ? 'Analysis Result' : 'বিশ্লেষণের ফলাফল'}
          </h2>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">{t('document.detectedType')}:</span>
            <DocTypeBadge type={result.detected_type} lang={result.language} />
          </div>
        </div>
        <button
          onClick={handleReset}
          className="text-sm text-slate-500 hover:text-slate-800 underline transition-colors"
        >
          {t('document.newAnalysis')}
        </button>
      </div>

      {/* Thumbnail */}
      {previewUrl && (
        <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
          <img src={previewUrl} alt="Analyzed" className="h-14 w-14 object-cover rounded-lg border border-slate-200 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-slate-700">{imgFile?.name}</p>
            <p className="text-xs text-slate-400">{imgFile ? formatSize(imgFile.size) : ''}</p>
          </div>
        </div>
      )}

      {/* Analysis card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <MarkdownContent text={result.analysis} />
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-3 justify-center">
        <button
          onClick={() => { void handleCopy(); }}
          className="inline-flex items-center gap-2 border border-slate-300 text-slate-600 hover:bg-slate-50 font-medium px-5 py-2.5 rounded-xl text-sm transition-colors"
        >
          {copied ? '✓ কপি হয়েছে' : '📋 বিশ্লেষণ কপি করুন'}
        </button>
        <button
          onClick={handleReset}
          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-colors"
        >
          🖼️ {t('document.newAnalysis')}
        </button>
      </div>

      {/* CTA */}
      <div className="text-center pt-2 pb-2 flex flex-col sm:flex-row items-center justify-center gap-3">
        <Link href="/lawyers" className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-8 py-4 rounded-xl text-base transition-colors shadow-md hover:shadow-lg">
          ⚖️ বিশেষজ্ঞ আইনজীবীর সাথে কথা বলুন →
        </Link>
        <Link href="/chat" className="inline-flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold px-6 py-4 rounded-xl text-base transition-colors border border-slate-200 shadow-sm">
          💬 AI-এ আরও প্রশ্ন করুন
        </Link>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DocumentPage() {
  const { t } = useLanguage();

  const [activeTab, setActiveTab] = useState<ActiveTab>('document');

  // Document tab state
  const [file,       setFile]       = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading,  setIsLoading]  = useState(false);
  const [result,     setResult]     = useState<AnalysisResult | null>(null);
  const [error,      setError]      = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const handleDragOver  = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(true); };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (!dropped) return;
    const err = validateDoc(dropped);
    if (err) { setError(err); return; }
    setFile(dropped); setError(null); setResult(null);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const chosen = e.target.files?.[0];
    if (!chosen) return;
    const err = validateDoc(chosen);
    if (err) { setError(err); return; }
    setFile(chosen); setError(null); setResult(null);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsLoading(true);
    setError(null);
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch(`${API_URL}/api/documents/analyze`, { method: 'POST', body: form });
      const data: unknown = await res.json();
      if (!res.ok) {
        setError(
          data !== null && typeof data === 'object' && 'detail' in data
            ? String((data as Record<string, unknown>).detail)
            : 'বিশ্লেষণ ব্যর্থ হয়েছে।'
        );
        return;
      }
      setResult(data as AnalysisResult);
    } catch {
      setError('সার্ভারের সাথে সংযোগ স্থাপন করা যায়নি।');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!result) return;
    setPdfLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/documents/report`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ filename: file?.name ?? 'document', ...result }),
      });
      if (!res.ok) { setError('PDF তৈরি করা যায়নি।'); return; }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url; a.download = `হ্যালো-এ্যাডভকেট-রিপোর্ট.pdf`;
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(url);
    } catch {
      setError('PDF ডাউনলোড করা যায়নি।');
    } finally {
      setPdfLoading(false);
    }
  };

  const handleDocReset = () => { setFile(null); setResult(null); setError(null); setPdfLoading(false); };

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* Hero */}
      <section style={{ background: 'linear-gradient(135deg, #064e3b 0%, #065f46 100%)' }} className="py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-yellow-400/20 border border-yellow-400/40 text-yellow-300 text-sm font-medium px-4 py-1.5 rounded-full mb-5">
            ⭐ প্রো সদস্যদের জন্য
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-white mb-4">{t('document.title')}</h1>
          <p className="text-emerald-100 text-lg max-w-2xl mx-auto leading-relaxed">
            আপনার আইনি ডকুমেন্ট বা ছবি আপলোড করুন — AI তা বিশ্লেষণ করে ঝুঁকি, গুরুত্বপূর্ণ শর্ত ও পরামর্শ দেবে।
          </p>
        </div>
      </section>

      {/* Tabs */}
      <div className="max-w-3xl mx-auto px-4 pt-8">
        <div className="flex gap-1 bg-slate-100 p-1 rounded-2xl">
          <button
            type="button"
            onClick={() => setActiveTab('document')}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              activeTab === 'document'
                ? 'bg-white text-emerald-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <span>📄</span>
            {t('document.tabDocument')}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('image')}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              activeTab === 'image'
                ? 'bg-white text-emerald-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <span>🖼️</span>
            {t('document.tabImage')}
          </button>
        </div>
      </div>

      {/* Content */}
      <section className="max-w-3xl mx-auto px-4 py-8">
        {activeTab === 'document' && (
          result ? (
            <DocResultSection
              result={result}
              filename={file?.name ?? ''}
              pdfLoading={pdfLoading}
              onReset={handleDocReset}
              onDownloadPdf={() => { void handleDownloadPdf(); }}
            />
          ) : (
            <>
              <DocUploadArea
                file={file}
                isDragging={isDragging}
                isLoading={isLoading}
                error={error}
                onDragOver={handleDragOver}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onFileChange={handleFileChange}
                onClear={handleDocReset}
                onAnalyze={() => { void handleAnalyze(); }}
              />
              {error && !file && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>
              )}
            </>
          )
        )}
        {activeTab === 'image' && <VisionTab />}
      </section>

      <footer className="border-t py-6 text-center text-sm text-slate-400">
        <p>⚠️ হ্যালো এ্যাডভকেট আইনি পরামর্শ নয় — গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর সাথে যোগাযোগ করুন।</p>
      </footer>
    </div>
  );
}
