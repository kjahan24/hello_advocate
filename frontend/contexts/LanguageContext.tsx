'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { translations, type Language } from '@/lib/translations';

// ─── Types ────────────────────────────────────────────────────────────────────

interface LanguageContextType {
  language:       Language;
  toggleLanguage: () => void;
  t:              (key: string) => string;
}

// ─── Context ──────────────────────────────────────────────────────────────────

const LanguageContext = createContext<LanguageContextType | null>(null);

// ─── Provider ─────────────────────────────────────────────────────────────────

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>('bn');
  const [mounted,  setMounted]  = useState(false);

  // Hydrate from localStorage after mount (avoids SSR mismatch)
  useEffect(() => {
    const stored = localStorage.getItem('language') as Language | null;
    if (stored === 'bn' || stored === 'en') {
      setLanguage(stored);
    }
    setMounted(true);
  }, []);

  const toggleLanguage = useCallback(() => {
    setLanguage((prev) => {
      const next = prev === 'bn' ? 'en' : 'bn';
      localStorage.setItem('language', next);
      return next;
    });
  }, []);

  // Traverse nested translation object with dotted key
  const t = useCallback(
    (key: string): string => {
      const parts = key.split('.');
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let obj: any = translations[language];
      for (const part of parts) {
        if (obj == null || typeof obj !== 'object') return key;
        obj = obj[part];
      }
      return typeof obj === 'string' ? obj : key;
    },
    [language],
  );

  // Suppress hydration flicker — render with 'bn' until client state is ready
  const ctxValue: LanguageContextType = { language: mounted ? language : 'bn', toggleLanguage, t };

  return (
    <LanguageContext.Provider value={ctxValue}>
      {children}
    </LanguageContext.Provider>
  );
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useLanguage(): LanguageContextType {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}
