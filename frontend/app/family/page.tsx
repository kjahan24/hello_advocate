'use client';

import Link from 'next/link';
import NavBar from '@/components/NavBar';
import { useLanguage } from '@/contexts/LanguageContext';

const SERVICES = [
  {
    icon: '💔',
    title: 'তালাক প্রক্রিয়া',
    desc: 'তালাক দেওয়া বা নেওয়ার নিয়ম জানুন',
    question: 'বাংলাদেশে মুসলিম আইনে তালাক দেওয়ার নিয়ম ও আইনি প্রক্রিয়া কী?',
  },
  {
    icon: '💰',
    title: 'দেনমোহর ও ভরণপোষণ',
    desc: 'দেনমোহর আদায় ও ভরণপোষণ পেতে করণীয়',
    question: 'তালাকের পর দেনমোহর ও ভরণপোষণ আইনত কীভাবে পাওয়া যায়?',
  },
  {
    icon: '🏠',
    title: 'উত্তরাধিকার বণ্টন',
    desc: 'মৃত্যুর পর সম্পত্তি বণ্টনের নিয়ম',
    question: 'বাংলাদেশে মুসলিম উত্তরাধিকার আইনে সম্পত্তি কীভাবে ভাগ হয়?',
  },
  {
    icon: '👶',
    title: 'শিশু হেফাজত',
    desc: 'তালাকের পর সন্তানের অভিভাবকত্ব',
    question: 'তালাকের পর শিশুর হেফাজত ও অভিভাবকত্বের অধিকার কার?',
  },
] as const;

const FAQS = [
  {
    q: 'বিবাহ নিবন্ধন কি বাধ্যতামূলক?',
    a: 'হ্যাঁ, মুসলিম পারিবারিক আইন অধ্যাদেশ ১৯৬১ অনুযায়ী বিবাহ নিবন্ধন বাধ্যতামূলক। নিবন্ধন না করলে কাবিননামা অনুযায়ী আইনি সুরক্ষা পাওয়া কঠিন হয়। নিকাহ রেজিস্ট্রার (কাজি) এই নিবন্ধন করেন।',
  },
  {
    q: 'খুলা তালাক কী এবং নারীরা কীভাবে তালাক নিতে পারেন?',
    a: 'খুলা হলো স্ত্রীর তালাক গ্রহণের পদ্ধতি — স্বামীকে দেনমোহর বা কিছু ফিরিয়ে দিয়ে বিচ্ছেদ। স্ত্রী চাইলে পারিবারিক আদালতে তালাকের মামলাও করতে পারেন। কাবিননামায় তালাকের ক্ষমতা থাকলে (তালাক-ই-তাওফিজ) স্ত্রী নিজেই তালাক দিতে পারেন।',
  },
  {
    q: 'দেনমোহর না দিলে কী শাস্তি হয়?',
    a: 'দেনমোহর স্ত্রীর আইনি পাওনা। স্বামী না দিলে পারিবারিক আদালতে মামলা করা যায়। আদালত নির্ধারিত সময়ের মধ্যে পরিশোধের আদেশ দেন। আদেশ না মানলে সম্পত্তি ক্রোক বা কারাদণ্ড হতে পারে।',
  },
  {
    q: 'বিদেশে থাকা স্বামীর বিরুদ্ধে কী করা যায়?',
    a: 'বিদেশে থাকা স্বামীর বিরুদ্ধে বাংলাদেশে পারিবারিক আদালতে মামলা করা যায়। বিবাদীকে নোটিশ পাঠানো হয়। ভরণপোষণ না পেলে নারী ও শিশু নির্যাতন দমন আইনেও মামলা হতে পারে।',
  },
  {
    q: 'মৃত বাবার সম্পত্তিতে মেয়েরা কতটুকু পাবেন?',
    a: 'মুসলিম উত্তরাধিকার আইনে মেয়ে ছেলের অর্ধেক পায়। তবে ছেলে না থাকলে মেয়ে মোট সম্পত্তির ১/২ পায়। দুই বা ততোধিক মেয়ে থাকলে মোট ২/৩ পান। হিন্দু আইনে ভিন্ন নিয়ম প্রযোজ্য।',
  },
] as const;

export default function FamilyPage() {
  const { t } = useLanguage();
  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      {/* Hero */}
      <section className="bg-emerald-700 py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-emerald-600 border border-emerald-500 text-emerald-100 text-sm font-medium px-4 py-1.5 rounded-full mb-5">
            👨‍👩‍👧 পারিবারিক আইন সেবা
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-white mb-4">
            পারিবারিক আইন
          </h1>
          <p className="text-emerald-100 text-lg max-w-2xl mx-auto leading-relaxed">
            বিবাহ, তালাক, দেনমোহর, ভরণপোষণ ও উত্তরাধিকার সংক্রান্ত
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
                href={`/chat?topic=family&q=${encodeURIComponent(s.question)}`}
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
            পারিবারিক আইন সম্পর্কে সাধারণ প্রশ্ন
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
            আপনার পারিবারিক সমস্যা লিখুন
          </h2>
          <p className="text-emerald-100 mb-8 text-base">
            AI আইনজীবী আপনার সমস্যা বিশ্লেষণ করে বাংলায় সমাধান দেবে
          </p>
          <Link
            href="/chat?topic=family"
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
