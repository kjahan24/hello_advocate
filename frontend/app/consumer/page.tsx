'use client';

import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const SERVICES = [
  {
    icon: '😤',
    title: 'প্রতারণার শিকার',
    desc: 'ভোক্তা অধিদপ্তরে অভিযোগ করার নিয়ম',
    question: 'পণ্য কিনে প্রতারিত হলে ভোক্তা অধিকার সংরক্ষণ অধিদপ্তরে কীভাবে অভিযোগ করব?',
  },
  {
    icon: '📦',
    title: 'অনলাইন কেনাকাটায় ঠকলে',
    desc: 'ই-কমার্স প্রতারণার আইনি সমাধান',
    question: 'অনলাইনে অর্ডার করে পণ্য না পেলে বা ভুল পণ্য পেলে কী করব?',
  },
  {
    icon: '🏦',
    title: 'ব্যাংক ও বীমা সমস্যা',
    desc: 'আর্থিক প্রতিষ্ঠানের বিরুদ্ধে অভিযোগ',
    question: 'ব্যাংক বা বীমা কোম্পানির অন্যায় সিদ্ধান্তের বিরুদ্ধে কোথায় ও কীভাবে অভিযোগ করব?',
  },
  {
    icon: '⚠️',
    title: 'পণ্যের মান সমস্যা',
    desc: 'ভেজাল ও নিম্নমানের পণ্যের বিরুদ্ধে ব্যবস্থা',
    question: 'ভেজাল বা নিম্নমানের পণ্য বিক্রেতার বিরুদ্ধে বাংলাদেশে কী আইনি ব্যবস্থা নেওয়া যায়?',
  },
] as const;

const FAQS = [
  {
    q: 'ভোক্তা অধিকার সংরক্ষণ আইন ২০০৯ কী?',
    a: 'ভোক্তা অধিকার সংরক্ষণ আইন ২০০৯ ক্রেতাদের প্রতারণা, ভেজাল পণ্য ও অসাধু ব্যবসায়িক চর্চার বিরুদ্ধে সুরক্ষা দেয়। এই আইনে জাতীয় ভোক্তা অধিকার সংরক্ষণ অধিদপ্তর প্রতিষ্ঠিত হয়েছে। দোষীদের কারাদণ্ড ও জরিমানার বিধান আছে।',
  },
  {
    q: 'অভিযোগ করতে কি টাকা লাগে?',
    a: 'না, ভোক্তা অধিকার সংরক্ষণ অধিদপ্তরে অভিযোগ বিনামূল্যে করা যায়। অনলাইনে (dncrp.gov.bd), হটলাইন ১৬১২১ নম্বরে বা সরাসরি অধিদপ্তরের অফিসে অভিযোগ করা যায়।',
  },
  {
    q: 'মেয়াদোত্তীর্ণ পণ্য বিক্রি করলে কী শাস্তি হয়?',
    a: 'মেয়াদোত্তীর্ণ পণ্য বিক্রির শাস্তি সর্বোচ্চ ১ বছরের কারাদণ্ড ও ৫০,০০০ টাকা জরিমানা। ভোক্তা অধিকার সংরক্ষণ আইন ২০০৯ এর ৪৫ ধারায় এই বিধান আছে। পুনরাবৃত্তিতে শাস্তি দ্বিগুণ হয়।',
  },
  {
    q: 'হোটেল-রেস্টুরেন্টে খারাপ সেবা পেলে কী করব?',
    a: 'প্রথমে ম্যানেজারের কাছে অভিযোগ করুন। সমাধান না হলে ভোক্তা অধিকার সংরক্ষণ অধিদপ্তরে অভিযোগ করুন। খাদ্যে ভেজাল বা অস্বাস্থ্যকর পরিবেশের ক্ষেত্রে নিরাপদ খাদ্য কর্তৃপক্ষেও অভিযোগ করতে পারেন।',
  },
  {
    q: 'ই-কমার্স কোম্পানির বিরুদ্ধে কোথায় অভিযোগ করব?',
    a: 'ই-কমার্স প্রতারণার ক্ষেত্রে ভোক্তা অধিকার সংরক্ষণ অধিদপ্তরে অভিযোগ করুন। বড় আর্থিক প্রতারণায় থানায় মামলা এবং ডিজিটাল নিরাপত্তা আইনেও ব্যবস্থা নেওয়া যায়। বাণিজ্য মন্ত্রণালয়ের অধীনে ই-কমার্স নীতিমালা ২০২১ প্রযোজ্য।',
  },
] as const;

export default function ConsumerPage() {
  const { t } = useLanguage();
  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* Hero */}
      <section className="bg-emerald-700 py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-emerald-600 border border-emerald-500 text-emerald-100 text-sm font-medium px-4 py-1.5 rounded-full mb-5">
            🛡️ ভোক্তা অধিকার সেবা
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-white mb-4">
            ভোক্তা অধিকার
          </h1>
          <p className="text-emerald-100 text-lg max-w-2xl mx-auto leading-relaxed">
            প্রতারণা, ভেজাল পণ্য, অনলাইন ঠকবাজি ও ব্যাংক-বীমা সমস্যায়
            আপনার অধিকার রক্ষায় বাংলায় সহায়তা পান।
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
                href={`/chat?topic=consumer&q=${encodeURIComponent(s.question)}`}
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
            ভোক্তা অধিকার সম্পর্কে সাধারণ প্রশ্ন
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
            আপনার ভোক্তা সমস্যা লিখুন
          </h2>
          <p className="text-emerald-100 mb-8 text-base">
            AI আইনজীবী আপনার সমস্যা বিশ্লেষণ করে বাংলায় সমাধান দেবে
          </p>
          <Link
            href="/chat?topic=consumer"
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
