'use client';

import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const SERVICES = [
  {
    icon: '📝',
    title: 'চুক্তিপত্র তৈরি',
    desc: 'আইনি চুক্তিপত্রের প্রয়োজনীয় শর্ত জানুন',
    question: 'ব্যবসায়িক চুক্তিপত্রে কী কী বিষয় থাকা আইনত প্রয়োজনীয়?',
  },
  {
    icon: '🪪',
    title: 'ট্রেড লাইসেন্স',
    desc: 'ট্রেড লাইসেন্স পাওয়ার প্রক্রিয়া জানুন',
    question: 'বাংলাদেশে ট্রেড লাইসেন্স পেতে কী কী করতে হবে এবং কত খরচ লাগে?',
  },
  {
    icon: '🏢',
    title: 'কোম্পানি নিবন্ধন',
    desc: 'কোম্পানি খোলার ধাপ ও আইনি নিয়ম',
    question: 'বাংলাদেশে প্রাইভেট লিমিটেড কোম্পানি নিবন্ধন করার নিয়ম ও প্রক্রিয়া কী?',
  },
  {
    icon: '💸',
    title: 'পাওনা আদায়',
    desc: 'ব্যবসায়িক পাওনা আইনিভাবে আদায় করুন',
    question: 'ব্যবসায়িক পাওনা আদায়ের জন্য বাংলাদেশে কী আইনি পদক্ষেপ নেওয়া যায়?',
  },
] as const;

const FAQS = [
  {
    q: 'প্রাইভেট লিমিটেড ও পার্টনারশিপের মধ্যে পার্থক্য কী?',
    a: 'প্রাইভেট লিমিটেড কোম্পানিতে শেয়ারহোল্ডারদের দায় সীমিত — ব্যক্তিগত সম্পদ ঝুঁকিতে পড়ে না। পার্টনারশিপে অংশীদারদের যৌথ ও পৃথক দায় অসীম। কোম্পানি আইন ১৯৯৪ ও পার্টনারশিপ আইন ১৯৩২ এ দুটি পৃথকভাবে নিয়ন্ত্রণ করে।',
  },
  {
    q: 'ব্যবসায়িক চুক্তি ভঙ্গ হলে কী করবেন?',
    a: 'চুক্তি ভঙ্গ হলে প্রথমে নোটিশ পাঠান। সমাধান না হলে দেওয়ানি আদালতে মামলা করুন বা আরবিট্রেশনে যান (চুক্তিতে আরবিট্রেশন ক্লজ থাকলে)। চুক্তিভঙ্গজনিত ক্ষতিপূরণ চুক্তি আইন ১৮৭২ এর ৭৩ ধারায় দাবি করা যায়।',
  },
  {
    q: 'VAT নিবন্ধন কখন বাধ্যতামূলক?',
    a: 'বার্ষিক টার্নওভার ৫০ লাখ টাকার বেশি হলে VAT নিবন্ধন বাধ্যতামূলক। ৩০ লাখ থেকে ৫০ লাখ টাকার মধ্যে টার্নওভার আপোষকারি হারে টার্নওভার ট্যাক্স প্রযোজ্য। নিবন্ধন না করে ব্যবসা করলে জরিমানা ও আইনি ব্যবস্থা হতে পারে।',
  },
  {
    q: 'মেধাস্বত্ব ও ট্রেডমার্ক রক্ষার নিয়ম কী?',
    a: 'ট্রেডমার্ক ডিপার্টমেন্ট অব পেটেন্টস, ডিজাইনস ও ট্রেডমার্কস (DPDT)-এ নিবন্ধন করতে হয়। কপিরাইটের জন্য কপিরাইট অফিসে নিবন্ধন করুন। অনুমোদন ছাড়া ব্যবহার হলে ট্রেডমার্ক আইন ২০০৯ ও কপিরাইট আইন ২০০০ এর আওতায় মামলা করা যায়।',
  },
  {
    q: 'কোম্পানি বন্ধ করতে হলে কী করতে হবে?',
    a: 'কোম্পানি স্বেচ্ছায় বন্ধ (Voluntary Winding Up) করতে সদস্যদের বিশেষ রেজোলিউশন পাস করতে হয়। RJSC-তে নির্ধারিত ফর্মে আবেদন করতে হয়। সব দায় পরিশোধের পর চূড়ান্ত নথি জমা দিলে কোম্পানি বিলুপ্ত হয়।',
  },
] as const;

export default function BusinessPage() {
  const { t } = useLanguage();
  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* Hero */}
      <section className="bg-emerald-700 py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-emerald-600 border border-emerald-500 text-emerald-100 text-sm font-medium px-4 py-1.5 rounded-full mb-5">
            💼 ব্যবসায়িক আইন সেবা
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-white mb-4">
            ব্যবসায়িক আইন
          </h1>
          <p className="text-emerald-100 text-lg max-w-2xl mx-auto leading-relaxed">
            কোম্পানি নিবন্ধন, চুক্তিপত্র, ট্রেড লাইসেন্স ও ব্যবসায়িক বিরোধ সংক্রান্ত
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
                href={`/chat?topic=business&q=${encodeURIComponent(s.question)}`}
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
            ব্যবসায়িক আইন সম্পর্কে সাধারণ প্রশ্ন
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
            আপনার ব্যবসায়িক সমস্যা লিখুন
          </h2>
          <p className="text-emerald-100 mb-8 text-base">
            AI আইনজীবী আপনার সমস্যা বিশ্লেষণ করে বাংলায় সমাধান দেবে
          </p>
          <Link
            href="/chat?topic=business"
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
