'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import DashboardSidebar from '@/components/DashboardSidebar';
import { getMe, updateProfile, changePassword, type UserProfile } from '@/lib/api';

// ─── helpers ─────────────────────────────────────────────────────────────────

const PLAN_LABELS: Record<string, string> = {
  free:       'বিনামূল্যে',
  pro:        'প্রো',
  lawyer:     'আইনজীবী',
  enterprise: 'এন্টারপ্রাইজ',
};
const PLAN_COLORS: Record<string, string> = {
  free:       'bg-slate-100 text-slate-700',
  pro:        'bg-emerald-100 text-emerald-700',
  lawyer:     'bg-blue-100 text-blue-700',
  enterprise: 'bg-purple-100 text-purple-700',
};

function extractDetail(err: unknown): string | null {
  if (
    err !== null &&
    typeof err === 'object' &&
    'response' in err
  ) {
    const res = (err as Record<string, unknown>).response;
    if (res !== null && typeof res === 'object' && 'data' in res) {
      const data = (res as Record<string, unknown>).data;
      if (data !== null && typeof data === 'object' && 'detail' in data) {
        const detail = (data as Record<string, unknown>).detail;
        if (typeof detail === 'string') return detail;
      }
    }
  }
  return null;
}

type FeedbackMsg = { type: 'success' | 'error'; text: string };

function Feedback({ msg }: { msg: FeedbackMsg | null }) {
  if (!msg) return null;
  return (
    <div
      className={`px-4 py-3 rounded-xl text-sm mb-4 ${
        msg.type === 'success'
          ? 'bg-emerald-50 border border-emerald-200 text-emerald-700'
          : 'bg-red-50 border border-red-200 text-red-700'
      }`}
    >
      {msg.text}
    </div>
  );
}

function UserAvatar({ name }: { name: string }) {
  const initials = name
    .trim()
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
  return (
    <div className="w-20 h-20 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold text-2xl mx-auto shadow-md">
      {initials || '?'}
    </div>
  );
}

// ─── page ─────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [profile,  setProfile]  = useState<UserProfile | null>(null);
  const [loading,  setLoading]  = useState(true);

  // profile form
  const [name,           setName]           = useState('');
  const [phone,          setPhone]          = useState('');
  const [profileSaving,  setProfileSaving]  = useState(false);
  const [profileMsg,     setProfileMsg]     = useState<FeedbackMsg | null>(null);

  // password form
  const [currentPw, setCurrentPw] = useState('');
  const [newPw,     setNewPw]     = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwSaving,  setPwSaving]  = useState(false);
  const [pwMsg,     setPwMsg]     = useState<FeedbackMsg | null>(null);

  useEffect(() => {
    if (status === 'unauthenticated') router.replace('/login');
  }, [status, router]);

  useEffect(() => {
    if (status !== 'authenticated') return;
    void getMe(session?.accessToken)
      .then((me) => {
        setProfile(me);
        setName(me.name ?? '');
        setPhone(me.phone ?? '');
      })
      .finally(() => setLoading(false));
  }, [status, session]);

  const handleProfileSave = async (e: FormEvent) => {
    e.preventDefault();
    setProfileMsg(null);
    setProfileSaving(true);
    try {
      const updated = await updateProfile(
        { name: name.trim(), phone: phone.trim() || null },
        session?.accessToken,
      );
      setProfile(updated);
      setName(updated.name ?? '');
      setPhone(updated.phone ?? '');
      setProfileMsg({ type: 'success', text: 'প্রোফাইল সফলভাবে সংরক্ষিত হয়েছে।' });
    } catch (err: unknown) {
      setProfileMsg({ type: 'error', text: extractDetail(err) ?? 'সংরক্ষণ করতে সমস্যা হয়েছে।' });
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordChange = async (e: FormEvent) => {
    e.preventDefault();
    setPwMsg(null);
    if (newPw !== confirmPw) {
      setPwMsg({ type: 'error', text: 'নতুন পাসওয়ার্ড দুটি মিলছে না।' });
      return;
    }
    setPwSaving(true);
    try {
      await changePassword(
        { current_password: currentPw, new_password: newPw },
        session?.accessToken,
      );
      setPwMsg({ type: 'success', text: 'পাসওয়ার্ড সফলভাবে পরিবর্তিত হয়েছে।' });
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
    } catch (err: unknown) {
      setPwMsg({ type: 'error', text: extractDetail(err) ?? 'পাসওয়ার্ড পরিবর্তন করতে সমস্যা হয়েছে।' });
    } finally {
      setPwSaving(false);
    }
  };

  const handleDeleteAccount = () => {
    if (window.confirm('আপনি কি সত্যিই আপনার অ্যাকাউন্ট মুছে ফেলতে চান? এই কাজ পূর্বাবস্থায় ফেরানো যাবে না।')) {
      window.alert('এই ফিচার শীঘ্রই আসছে।');
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen flex">
        <DashboardSidebar />
        <main className="lg:ml-64 flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin" />
        </main>
      </div>
    );
  }

  if (!session || !profile) return null;

  const planLabel = PLAN_LABELS[profile.plan] ?? profile.plan;
  const planColor = PLAN_COLORS[profile.plan] ?? PLAN_COLORS.free;
  const inputClass =
    'w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm transition-all';

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <DashboardSidebar />

      <main className="lg:ml-64 flex-1 p-6 pt-16 lg:pt-8 max-w-2xl">

        {/* Avatar + plan */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6 text-center">
          <UserAvatar name={profile.name ?? profile.email} />
          <h1 className="text-xl font-bold text-slate-800 mt-4">
            {profile.name ?? '—'}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">{profile.email}</p>
          <div className="flex items-center justify-center gap-2 mt-3 flex-wrap">
            <span className={`text-xs font-semibold px-3 py-1 rounded-full ${planColor}`}>
              {planLabel}
            </span>
            <span className="text-xs text-slate-400">{profile.role === 'lawyer' ? 'আইনজীবী' : 'নাগরিক'}</span>
          </div>
          {profile.plan === 'free' && (
            <button className="mt-4 text-sm bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-5 py-2 rounded-xl transition-colors shadow-sm">
              আপগ্রেড করুন → প্রো
            </button>
          )}
        </div>

        {/* Edit profile */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6">
          <h2 className="text-base font-semibold text-slate-800 mb-5">প্রোফাইল সম্পাদনা</h2>
          <Feedback msg={profileMsg} />
          <form onSubmit={(e) => { void handleProfileSave(e); }} className="space-y-4">

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">পূর্ণ নাম</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="আপনার পূর্ণ নাম"
                className={inputClass}
              />
            </div>

            {/* Email (read-only) */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                ইমেইল ঠিকানা
                <span className="ml-1.5 text-xs text-slate-400 font-normal">🔒 পরিবর্তনযোগ্য নয়</span>
              </label>
              <input
                type="email"
                value={profile.email}
                disabled
                className="w-full px-4 py-3 rounded-xl border border-slate-100 bg-slate-50 text-slate-400 text-sm cursor-not-allowed"
              />
            </div>

            {/* Phone */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                ফোন নম্বর
                <span className="ml-1.5 text-xs text-slate-400 font-normal">(ঐচ্ছিক)</span>
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+880 1X-XXXXXXXX"
                className={inputClass}
              />
            </div>

            <button
              type="submit"
              disabled={profileSaving}
              className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-semibold py-3 rounded-xl transition-colors text-sm shadow-sm"
            >
              {profileSaving ? 'সংরক্ষণ হচ্ছে…' : 'সংরক্ষণ করুন'}
            </button>
          </form>
        </div>

        {/* Change password */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6">
          <h2 className="text-base font-semibold text-slate-800 mb-5">পাসওয়ার্ড পরিবর্তন</h2>
          <Feedback msg={pwMsg} />
          <form onSubmit={(e) => { void handlePasswordChange(e); }} className="space-y-4">

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">বর্তমান পাসওয়ার্ড</label>
              <input
                type="password"
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="বর্তমান পাসওয়ার্ড লিখুন"
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">নতুন পাসওয়ার্ড</label>
              <input
                type="password"
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
                required
                minLength={6}
                autoComplete="new-password"
                placeholder="কমপক্ষে ৬ অক্ষর"
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">নতুন পাসওয়ার্ড নিশ্চিত করুন</label>
              <input
                type="password"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="পাসওয়ার্ড আবার লিখুন"
                className={inputClass}
              />
            </div>

            <button
              type="submit"
              disabled={pwSaving}
              className="w-full bg-slate-800 hover:bg-slate-900 disabled:bg-slate-400 text-white font-semibold py-3 rounded-xl transition-colors text-sm shadow-sm"
            >
              {pwSaving ? 'পরিবর্তন হচ্ছে…' : 'পাসওয়ার্ড পরিবর্তন করুন'}
            </button>
          </form>
        </div>

        {/* Danger zone */}
        <div className="bg-white border border-red-200 rounded-2xl p-6 shadow-sm">
          <h2 className="text-base font-semibold text-red-700 mb-2">বিপদ অঞ্চল</h2>
          <p className="text-sm text-slate-500 mb-4">
            অ্যাকাউন্ট মুছে ফেলা হলে আপনার সমস্ত ডেটা স্থায়ীভাবে মুছে যাবে।
          </p>
          <button
            onClick={handleDeleteAccount}
            className="text-sm bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors shadow-sm"
          >
            অ্যাকাউন্ট মুছুন
          </button>
        </div>

      </main>
    </div>
  );
}
