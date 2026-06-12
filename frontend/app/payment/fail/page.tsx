import Link from 'next/link';

export default function PaymentFailPage() {
  return (
    <div className="min-h-screen bg-red-50 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-10 text-center">
        <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <span className="text-4xl">❌</span>
        </div>
        <h1 className="text-2xl font-bold text-red-800 mb-3">
          পেমেন্ট ব্যর্থ হয়েছে
        </h1>
        <p className="text-slate-600 mb-8 leading-relaxed">
          আপনার পেমেন্ট সম্পন্ন হয়নি। কোনো টাকা কাটা হয়নি।
          পুনরায় চেষ্টা করুন অথবা ভিন্ন পেমেন্ট পদ্ধতি ব্যবহার করুন।
        </p>
        <div className="flex flex-col gap-3">
          <Link
            href="/pricing"
            className="block bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-6 py-3 rounded-xl transition-colors"
          >
            পুনরায় চেষ্টা করুন
          </Link>
          <Link
            href="/"
            className="block bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-6 py-3 rounded-xl transition-colors"
          >
            হোম পেজে ফিরুন
          </Link>
        </div>
      </div>
    </div>
  );
}
