'use client';

import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const SERVICES = [
  {
    icon: '📄',
    title: 'দলিল বিশ্লেষণ',
    desc: 'আপনার জমির দলিল সম্পর্কে প্রশ্ন করুন',
    question: 'আমার জমির দলিলে কী কী বিষয় যাচাই করতে হবে?',
  },
  {
    icon: '🏛️',
    title: 'নামজারি ও খারিজ',
    desc: 'নামজারি প্রক্রিয়া জানুন',
    question: 'জমির নামজারি বা মিউটেশন করতে কী কী কাগজপত্র লাগে এবং প্রক্রিয়া কী?',
  },
  {
    icon: '🤝',
    title: 'জমি কেনাবেচা',
    desc: 'আইনি চেকলিস্ট দেখুন',
    question: 'বাংলাদেশে জমি কেনার সময় আইনি দিক থেকে কী কী বিষয় যাচাই করতে হবে?',
  },
  {
    icon: '⚔️',
    title: 'সীমানা বিরোধ',
    desc: 'সমাধানের পথ জানুন',
    question: 'প্রতিবেশীর সাথে জমির সীমানা বিরোধে আইনি সমাধান কী?',
  },
] as const;

const FAQS = [
  {
    q: 'জমির দলিল কত প্রকার?',
    a: 'বাংলাদেশে প্রধান দলিলের মধ্যে আছে: বায়না দলিল, সাফ কবলা দলিল, হেবা দলিল, ওয়ারিশান দলিল এবং বন্টননামা দলিল। প্রতিটির আলাদা আইনি কার্যকারিতা রয়েছে।',
  },
  {
    q: 'নামজারি না করলে কী সমস্যা হয়?',
    a: 'নামজারি না করলে সরকারি রেকর্ডে জমি আগের মালিকের নামেই থাকে। এতে ভূমি কর পরিশোধে সমস্যা, ব্যাংক ঋণে জামানত দেওয়া এবং পরবর্তীতে জমি বিক্রিতে জটিলতা হয়।',
  },
  {
    q: 'জমি রেজিস্ট্রেশন ফি কত?',
    a: 'বাংলাদেশে জমি রেজিস্ট্রেশনে মোট ব্যয় প্রায় ৮-১০% হয়: রেজিস্ট্রেশন ফি ১%, স্ট্যাম্প শুল্ক ১.৫%, ই-ফি ১%, স্থানীয় সরকার কর ২%, এবং উৎসে কর সর্বোচ্চ ৩%।',
  },
  {
    q: 'ওয়ারিশান সম্পত্তিতে ভাগ কীভাবে হয়?',
    a: 'মুসলিম আইনে মৃত ব্যক্তির সম্পত্তি কোরআনিক নিয়ম অনুযায়ী ভাগ হয়। ছেলে মেয়ের দ্বিগুণ পায়। হিন্দু আইনে হিন্দু উত্তরাধিকার আইন ১৯২৮ প্রযোজ্য।',
  },
  {
    q: 'জমি অধিগ্রহণে ক্ষতিপূরণ পাওয়ার নিয়ম কী?',
    a: 'অধিগ্রহণ ও পুনর্বাসন আইন ২০১৭ অনুযায়ী, সরকার জমি অধিগ্রহণ করলে বাজারমূল্যের ৩ গুণ ক্ষতিপূরণ দিতে বাধ্য। নোটিশ পাওয়ার ১৫ দিনের মধ্যে আপত্তি জানানো যায়।',
  },
] as const;

export default function LandPage() {
  const { t } = useLanguage();
  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* Hero */}
      <section className="bg-emerald-700 py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-emerald-600 border border-emerald-500 text-emerald-100 text-sm font-medium px-4 py-1.5 rounded-full mb-5">
            🏡 ভূমি আইন সেবা
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-white mb-4">
            জমি ও সম্পত্তি আইন
          </h1>
          <p className="text-emerald-100 text-lg max-w-2xl mx-auto leading-relaxed">
            বাংলাদেশের ভূমি আইন, নামজারি, দলিল ও সম্পত্তি বিরোধ সংক্রান্ত
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
                href={`/chat?topic=land&q=${encodeURIComponent(s.question)}`}
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
            জমি আইন সম্পর্কে সাধারণ প্রশ্ন
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
            আপনার জমি সংক্রান্ত সমস্যা লিখুন
          </h2>
          <p className="text-emerald-100 mb-8 text-base">
            AI আইনজীবী আপনার সমস্যা বিশ্লেষণ করে বাংলায় সমাধান দেবে
          </p>
          <Link
            href="/chat?topic=land"
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
