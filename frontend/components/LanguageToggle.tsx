'use client';

import { useLanguage } from '@/contexts/LanguageContext';

export default function LanguageToggle() {
  const { language, toggleLanguage } = useLanguage();

  return (
    <button
      onClick={toggleLanguage}
      aria-label="Toggle language"
      className="flex items-center rounded-full border border-slate-200 bg-slate-50 hover:bg-slate-100 transition-colors text-xs font-semibold overflow-hidden flex-shrink-0"
    >
      <span
        className={`px-2.5 py-1.5 transition-colors ${
          language === 'bn'
            ? 'bg-emerald-600 text-white'
            : 'text-slate-500 hover:text-slate-700'
        }`}
      >
        বাং
      </span>
      <span
        className={`px-2.5 py-1.5 transition-colors ${
          language === 'en'
            ? 'bg-emerald-600 text-white'
            : 'text-slate-500 hover:text-slate-700'
        }`}
      >
        EN
      </span>
    </button>
  );
}
