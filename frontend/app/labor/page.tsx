'use client';

import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const SERVICES = [
  {
    icon: '🚫',
    title: 'অন্যায় বরখাস্ত',
    desc: 'বেআইনি ছাঁটাইয়ের বিরুদ্ধে আইনি পদক্ষেপ',
    question: 'নোটিশ ছাড়া বা অন্যায়ভাবে চাকরি থেকে বরখাস্ত হলে কী করব?',
  },
  {
    icon: '💵',
    title: 'বকেয়া বেতন',
    desc: 'বেতন না পেলে আইনি সমাধান',
    question: 'মালিক বেতন না দিলে বা বকেয়া রাখলে শ্রম আইনে কী ব্যবস্থা নেওয়া যায়?',
  },
  {
    icon: '🛑',
    title: 'কর্মক্ষেত্রে হয়রানি',
    desc: 'নিপীড়ন ও হয়রানির বিরুদ্ধে করণীয়',
    question: 'কর্মক্ষেত্রে যৌন হয়রানি বা নিপীড়নের বিরুদ্ধে বাংলাদেশে আইনি প্রতিকার কী?',
  },
  {
    icon: '📅',
    title: 'ছুটি ও ক্ষতিপূরণ',
    desc: 'আপনার প্রাপ্য ছুটি ও গ্র্যাচুইটি জানুন',
    question: 'বাংলাদেশ শ্রম আইনে কত দিন ছুটি পাওয়ার অধিকার আছে এবং গ্র্যাচুইটি কীভাবে পাব?',
  },
] as const;

const FAQS = [
  {
    q: 'চাকরিচ্যুতিতে কত দিনের নোটিশ দিতে হয়?',
    a: 'বাংলাদেশ শ্রম আইন ২০০৬ অনুযায়ী স্থায়ী কর্মীকে ১২০ দিনের নোটিশ বা নোটিশ পে দিতে হয়। অস্থায়ী কর্মীর জন্য ৩০ দিন। নোটিশ না দিয়ে বরখাস্ত করলে সম্পূর্ণ পে দিতে হবে।',
  },
  {
    q: 'গ্র্যাচুইটি কখন পাওয়া যায়?',
    a: 'এক বছরের বেশি চাকরি করলে গ্র্যাচুইটির অধিকার জন্মায়। প্রতি বছরের জন্য শেষ মাসিক মূল বেতনের ৩০ দিনের সমপরিমাণ গ্র্যাচুইটি পাওয়া যায়। পদত্যাগ, অবসর বা ছাঁটাই — সব ক্ষেত্রে প্রযোজ্য।',
  },
  {
    q: 'ট্রেড ইউনিয়নে যোগ দেওয়া কি আইনসম্মত?',
    a: 'হ্যাঁ, বাংলাদেশ শ্রম আইন অনুযায়ী শ্রমিকদের ট্রেড ইউনিয়ন গঠন ও যোগদানের অধিকার আছে। ইউনিয়নে যোগ দেওয়ার কারণে চাকরি থেকে বরখাস্ত করলে তা বেআইনি এবং আইনি পদক্ষেপ নেওয়া যাবে।',
  },
  {
    q: 'মাতৃত্বকালীন ছুটি কত দিন এবং বেতন পাওয়া যায়?',
    a: 'বাংলাদেশ শ্রম আইনে মাতৃত্বকালীন ছুটি ১৬ সপ্তাহ (৮ সপ্তাহ আগে + ৮ সপ্তাহ পরে)। এই সময়ে পূর্ণ বেতন পাওয়ার অধিকার আছে। প্রথম দুটি সন্তানের জন্য এই সুবিধা প্রযোজ্য।',
  },
  {
    q: 'কর্মক্ষেত্রে দুর্ঘটনায় ক্ষতিপূরণ পাওয়ার নিয়ম কী?',
    a: 'কর্মক্ষেত্রে দুর্ঘটনায় আহত বা নিহত হলে নিয়োগকর্তা ক্ষতিপূরণ দিতে বাধ্য। বাংলাদেশ শ্রম আইনের ১৫১-১৭৩ ধারায় ক্ষতিপূরণের পরিমাণ নির্ধারিত। স্থায়ী পঙ্গুত্বে সর্বোচ্চ ১,২৫,০০০ টাকা ক্ষতিপূরণ দেওয়ার বিধান আছে।',
  },
] as const;

export default function LaborPage() {
  const { t } = useLanguage();
  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* Hero */}
      <section className="bg-emerald-700 py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-emerald-600 border border-emerald-500 text-emerald-100 text-sm font-medium px-4 py-1.5 rounded-full mb-5">
            ⚒️ শ্রম আইন সেবা
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-white mb-4">
            শ্রম আইন
          </h1>
          <p className="text-emerald-100 text-lg max-w-2xl mx-auto leading-relaxed">
            বেতন, ছুটি, বরখাস্ত, গ্র্যাচুইটি ও কর্মক্ষেত্রের অধিকার সংক্রান্ত
            যেকোনো প্রশ্নের উত্তর পান বাংলায়।
          </p>
        </div>
      </section>

      {/* Service Cards */}
      <section className="max-w-5xl mx-auto px-4 py-14">
        <h2 className="text-2xl font-bold text-slate-800 text-center mb-8">
          কোন বিষয়ে সাহায্য দরকার?
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {SERVICES.map((s) => (
            <div
              key={s.title}
              className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col gap-4 hover:shadow-md transition-shadow"
            >
              <div className="text-3xl">{s.icon}</div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-800 text-base mb-1">{s.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{s.desc}</p>
              </div>
              <Link
                href={`/chat?topic=labor&q=${encodeURIComponent(s.question)}`}
                className="inline-flex items-center gap-1 text-sm font-semibold text-emerald-600 hover:text-emerald-700 transition-colors"
              >
                {t('services.askQuestion')}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-white">
        <div className="max-w-3xl mx-auto px-4 py-16">
          <h2 className="text-2xl font-bold text-slate-800 text-center mb-8">
            শ্রম আইন সম্পর্কে সাধারণ প্রশ্ন
          </h2>
          <div className="space-y-3">
            {FAQS.map((item) => (
              <details
                key={item.q}
                className="group bg-slate-50 border border-slate-200 rounded-xl overflow-hidden"
              >
                <summary className="flex items-center justify-between px-6 py-4 cursor-pointer list-none font-medium text-slate-800 hover:bg-slate-100 transition-colors">
                  {item.q}
                  <span className="ml-4 flex-shrink-0 text-slate-400 group-open:rotate-180 transition-transform duration-200">
                    ▼
                  </span>
                </summary>
                <p className="px-6 pb-4 text-slate-600 text-sm leading-relaxed">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-emerald-700">
        <div className="max-w-3xl mx-auto px-4 py-16 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">
            আপনার শ্রম সংক্রান্ত সমস্যা লিখুন
          </h2>
          <p className="text-emerald-100 mb-8 text-base">
            AI আইনজীবী আপনার সমস্যা বিশ্লেষণ করে বাংলায় সমাধান দেবে
          </p>
          <Link
            href="/chat?topic=labor"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white hover:bg-slate-100 text-emerald-700 font-bold px-8 py-4 rounded-xl text-base transition-colors shadow-md hover:shadow-lg"
          >
            এখনই প্রশ্ন করুন →
          </Link>
        </div>
      </section>

      <footer className="border-t py-6 text-center text-sm text-slate-400">
        <p>
          ⚠️ হ্যালো এ্যাডভকেট আইনি পরামর্শ নয় — গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর
          সাথে যোগাযোগ করুন।
        </p>
      </footer>
    </div>
  );
}
