import Link from 'next/link';

export default function PaymentCancelPage() {
  return (
    <div className="min-h-screen bg-yellow-50 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-10 text-center">
        <div className="w-20 h-20 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <span className="text-4xl">↩️</span>
        </div>
        <h1 className="text-2xl font-bold text-yellow-800 mb-3">
          পেমেন্ট বাতিল করা হয়েছে
        </h1>
        <p className="text-slate-600 mb-8 leading-relaxed">
          আপনি পেমেন্ট বাতিল করেছেন। কোনো টাকা কাটা হয়নি।
          যেকোনো সময় আবার সাবস্ক্রাইব করতে পারবেন।
        </p>
        <div className="flex flex-col gap-3">
          <Link
            href="/pricing"
            className="block bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-6 py-3 rounded-xl transition-colors"
          >
            মূল্য তালিকায় ফিরুন
          </Link>
          <Link
            href="/chat"
            className="block bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-6 py-3 rounded-xl transition-colors"
          >
            বিনামূল্যে ব্যবহার করুন
          </Link>
        </div>
      </div>
    </div>
  );
}
