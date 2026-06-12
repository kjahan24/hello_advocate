'use client';

import { useRef } from 'react';

const ACCEPTED = '.jpg,.jpeg,.png,.gif,.webp,.pdf';
const MAX_MB   = { image: 10, pdf: 32 } as const;

interface Props {
  onFileSelect: (file: File) => void;
  disabled?:    boolean;
}

export default function FileUploadButton({ onFileSelect, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const isPdf    = file.type === 'application/pdf';
    const maxBytes = (isPdf ? MAX_MB.pdf : MAX_MB.image) * 1024 * 1024;

    if (file.size > maxBytes) {
      alert(
        `ফাইলটি অনেক বড়। সর্বোচ্চ ${isPdf ? MAX_MB.pdf : MAX_MB.image} MB।\n` +
        `File too large. Max ${isPdf ? MAX_MB.pdf : MAX_MB.image} MB.`,
      );
      e.target.value = '';
      return;
    }

    onFileSelect(file);
    e.target.value = ''; // allow re-selecting the same file
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={handleChange}
        disabled={disabled}
        aria-label="দলিল বা ছবি আপলোড করুন"
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled}
        title="দলিল / ছবি আপলোড করুন (PDF, JPG, PNG…)"
        className="flex-shrink-0 w-11 h-11 rounded-2xl border border-slate-200 bg-white hover:bg-emerald-50 hover:border-emerald-300 disabled:opacity-40 text-slate-500 hover:text-emerald-700 flex items-center justify-center transition-colors"
      >
        <PaperclipIcon />
      </button>
    </>
  );
}

function PaperclipIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
      />
    </svg>
  );
}
