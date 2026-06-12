import Link from 'next/link';

export default function PaymentSuccessPage() {
  return (
    <div className="min-h-screen bg-emerald-50 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-10 text-center">
        <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <span className="text-4xl">🎉</span>
        </div>
        <h1 className="text-2xl font-bold text-emerald-800 mb-3">
          পেমেন্ট সফল হয়েছে!
        </h1>
        <p className="text-slate-600 mb-2 leading-relaxed">
          আপনার প্রো সদস্যপদ সক্রিয় হয়েছে।
          এখন থেকে সীমাহীন প্রশ্ন ও ডকুমেন্ট বিশ্লেষণ উপভোগ করুন।
        </p>
        <p className="text-sm text-slate-400 mb-8">
          একটি নিশ্চিতকরণ ইমেইল পাঠানো হয়েছে।
        </p>
        <div className="flex flex-col gap-3">
          <Link
            href="/chat"
            className="block bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-6 py-3 rounded-xl transition-colors"
          >
            AI আইনজীবীর সাথে কথা বলুন →
          </Link>
          <Link
            href="/dashboard"
            className="block bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-6 py-3 rounded-xl transition-colors"
          >
            ড্যাশবোর্ড দেখুন
          </Link>
        </div>
      </div>
    </div>
  );
}
