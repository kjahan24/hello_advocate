interface Props {
  onSelect: (question: string) => void;
}

const SUGGESTIONS = [
  { bn: 'চুরির শাস্তি কী?',              en: 'Theft punishment?'      },
  { bn: 'তালাকের জন্য কী করতে হবে?',     en: 'Divorce procedure?'     },
  { bn: 'আমার শ্রমিক অধিকার কী কী?',     en: 'Labour rights?'         },
  { bn: 'দণ্ডবিধির ধারা ৩০২ কী?',        en: 'Penal Code section 302?'},
  { bn: 'ভূমি রেজিস্ট্রেশন প্রক্রিয়া কী?', en: 'Land registration?'    },
  { bn: 'ডিজিটাল নিরাপত্তা আইন কী?',      en: 'Digital Security Act?'  },
];

export default function SuggestedQuestions({ onSelect }: Props) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8">
      {/* Logo */}
      <div className="w-16 h-16 rounded-2xl bg-emerald-600 flex items-center justify-center shadow-lg mb-6">
        <span className="text-white text-3xl font-bold">আ</span>
      </div>
      <h2 className="text-2xl font-bold text-slate-800 mb-1 text-center">
        AI Lawyer
      </h2>
      <p className="text-slate-500 text-center mb-10 max-w-md">
        বাংলাদেশের যেকোনো আইন সম্পর্কে প্রশ্ন করুন — বাংলায় বা ইংরেজিতে।
      </p>

      {/* Suggestions */}
      <div className="grid sm:grid-cols-2 gap-3 w-full max-w-xl">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.en}
            type="button"
            onClick={() => onSelect(s.bn)}
            className="text-left px-4 py-3 rounded-xl border border-slate-200 bg-white hover:border-emerald-300 hover:bg-emerald-50 transition-colors group"
          >
            <p className="text-sm font-medium text-slate-800 group-hover:text-emerald-800">
              {s.bn}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">{s.en}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
