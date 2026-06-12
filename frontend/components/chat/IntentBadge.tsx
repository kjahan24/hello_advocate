import type { IntentData } from '@/types';
import { cn } from '@/lib/utils';

const CATEGORY_LABELS: Record<string, string> = {
  criminal:            'ফৌজদারি',
  civil:               'দেওয়ানি',
  family:              'পারিবারিক',
  land_property:       'ভূমি ও সম্পত্তি',
  labor_employment:    'শ্রম ও কর্মসংস্থান',
  constitutional:      'সাংবিধানিক',
  commercial_business: 'বাণিজ্য',
  banking_finance:     'ব্যাংকিং',
  tenancy_rent:        'ভাড়া',
  consumer_rights:     'ভোক্তা অধিকার',
  digital_cyber:       'ডিজিটাল',
  immigration:         'অভিবাসন',
};

const INTENT_LABELS: Record<string, string> = {
  FIND_LAW:      'আইন অনুসন্ধান',
  FIND_SECTION:  'ধারা অনুসন্ধান',
  FIND_CASE:     'মামলার নজির',
  EXPLAIN_RIGHTS:'অধিকার ব্যাখ্যা',
  CHECK_PROCESS: 'প্রক্রিয়া',
  COMPARE_LAWS:  'আইন তুলনা',
  GET_DOCUMENT:  'দলিল',
  GENERAL_INFO:  'সাধারণ তথ্য',
  UNKNOWN:       'অজ্ঞাত',
};

const CATEGORY_COLORS: Record<string, string> = {
  criminal:            'bg-red-50    text-red-700    border-red-200',
  civil:               'bg-blue-50   text-blue-700   border-blue-200',
  family:              'bg-pink-50   text-pink-700   border-pink-200',
  land_property:       'bg-amber-50  text-amber-700  border-amber-200',
  labor_employment:    'bg-violet-50 text-violet-700 border-violet-200',
  constitutional:      'bg-cyan-50   text-cyan-700   border-cyan-200',
  commercial_business: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  banking_finance:     'bg-teal-50   text-teal-700   border-teal-200',
  tenancy_rent:        'bg-orange-50 text-orange-700 border-orange-200',
  consumer_rights:     'bg-lime-50   text-lime-700   border-lime-200',
  digital_cyber:       'bg-sky-50    text-sky-700    border-sky-200',
  immigration:         'bg-rose-50   text-rose-700   border-rose-200',
};

interface Props {
  intent: IntentData;
}

export default function IntentBadge({ intent }: Props) {
  const categoryClass =
    CATEGORY_COLORS[intent.category] ??
    'bg-slate-50 text-slate-700 border-slate-200';

  const intentLabel = INTENT_LABELS[intent.intent] ?? intent.intent;
  const categoryLabel = CATEGORY_LABELS[intent.category] ?? intent.category;
  const stageLabel = intent.stage === 1 ? '⚡ Stage 1' : '🧠 Stage 2';

  return (
    <div className="flex flex-wrap items-center gap-1.5 mb-3 animate-fade-in">
      <span
        className={cn(
          'inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full border',
          categoryClass,
        )}
      >
        {categoryLabel}
      </span>
      <span className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
        {intentLabel}
      </span>
      <span className="inline-flex items-center gap-1 text-xs text-slate-400 px-2 py-1">
        {stageLabel} · {Math.round(intent.confidence * 100)}%
      </span>
    </div>
  );
}
