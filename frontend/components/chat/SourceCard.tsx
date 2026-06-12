'use client';

import { useState } from 'react';
import type { SourceItem } from '@/types';
import { cn } from '@/lib/utils';

interface Props {
  source: SourceItem;
  index: number;
}

export default function SourceCard({ source, index }: Props) {
  const [expanded, setExpanded] = useState(false);
  const score = Math.round(source.relevance_score * 100);

  if (source.source_type === 'case') {
    return (
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden text-sm animate-fade-in">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="w-full text-left px-4 py-3 flex items-start justify-between gap-2 hover:bg-slate-50 transition-colors"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-xs font-semibold text-slate-400">
                #{index + 1} · মামলার নজির
              </span>
              <RelevanceBar score={score} />
            </div>
            <p className="font-medium text-slate-800 truncate">
              {source.citation ?? 'Unknown Citation'}
            </p>
            {source.court && (
              <p className="text-xs text-slate-500 mt-0.5">{source.court}</p>
            )}
          </div>
          <ChevronIcon expanded={expanded} />
        </button>

        {expanded && (
          <div className="px-4 pb-4 border-t border-slate-100 pt-3 space-y-2">
            {source.parties && (
              <p className="text-slate-700">
                <span className="font-medium">পক্ষ: </span>
                {source.parties}
              </p>
            )}
            {source.summary && (
              <p className="text-slate-600 leading-relaxed">{source.summary}</p>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden text-sm animate-fade-in">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-4 py-3 flex items-start justify-between gap-2 hover:bg-slate-50 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-semibold text-slate-400">
              #{index + 1}
              {source.section_number ? ` · ধারা ${source.section_number}` : ''}
            </span>
            <RelevanceBar score={score} />
          </div>
          <p className="font-medium text-slate-800 truncate">
            {source.act_title_en ?? 'Unknown Act'}
            {source.year ? ` (${source.year})` : ''}
          </p>
          {source.section_title && (
            <p className="text-xs text-slate-500 mt-0.5 truncate">
              {source.section_title}
            </p>
          )}
        </div>
        <ChevronIcon expanded={expanded} />
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-100 pt-3 space-y-2">
          {source.content_en && (
            <p className="text-slate-700 leading-relaxed whitespace-pre-wrap text-xs">
              {source.content_en.length > 600
                ? `${source.content_en.slice(0, 600)}…`
                : source.content_en}
            </p>
          )}
          {source.content_bn && (
            <p className="text-slate-600 leading-relaxed font-bengali text-xs">
              {source.content_bn.length > 400
                ? `${source.content_bn.slice(0, 400)}…`
                : source.content_bn}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function RelevanceBar({ score }: { score: number }) {
  const color =
    score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-amber-400' : 'bg-slate-300';

  return (
    <div className="flex items-center gap-1">
      <div className="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full', color)}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs text-slate-400">{score}%</span>
    </div>
  );
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      className={cn(
        'w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5 transition-transform',
        expanded && 'rotate-180',
      )}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 9l-7 7-7-7"
      />
    </svg>
  );
}
