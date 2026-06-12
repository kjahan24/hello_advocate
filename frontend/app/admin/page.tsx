'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useLanguage } from '@/contexts/LanguageContext';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

type Tab = 'overview' | 'users' | 'revenue' | 'activity';

interface Stats {
  total_users: number;
  new_users_today: number;
  new_users_week: number;
  total_chats: number;
  chats_today: number;
  pro_users: number;
  free_users: number;
  student_users: number;
  total_revenue: number;
  monthly_revenue: number;
  total_documents: number;
  total_cases: number;
  active_users_today: number;
  total_lawyers: number;
  verified_lawyers: number;
  total_subscriptions: number;
  active_subscriptions: number;
}

interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  plan: string;
  is_admin: boolean;
  is_active: boolean;
  query_count_today: number;
  query_limit: number;
  total_chats: number;
  created_at: string | null;
}

interface UserListResponse {
  users: AdminUser[];
  total: number;
  page: number;
  pages: number;
}

interface MonthlyRevenue {
  month: string;
  revenue: number;
  new_pro: number;
}

interface RevenueData {
  monthly: MonthlyRevenue[];
  total_revenue: number;
  mrr: number;
}

interface ActivityItem {
  type: string;
  description: string;
  time: string;
  detail: string | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function planBadge(plan: string) {
  const map: Record<string, string> = {
    pro:     'bg-amber-100 text-amber-800',
    student: 'bg-blue-100 text-blue-800',
    lawyer:  'bg-purple-100 text-purple-800',
    free:    'bg-slate-100 text-slate-600',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${map[plan] ?? 'bg-slate-100 text-slate-600'}`}>
      {plan}
    </span>
  );
}

function Toggle({ checked, onChange, disabled = false }: { checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onChange}
      disabled={disabled}
      className={`relative inline-flex w-9 h-5 rounded-full transition-colors disabled:opacity-40 ${checked ? 'bg-emerald-500' : 'bg-slate-300'}`}
    >
      <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-4' : ''}`} />
    </button>
  );
}

function timeAgo(iso: string, t: (key: string) => string): string {
  const diffMs  = Date.now() - new Date(iso).getTime();
  const mins    = Math.floor(diffMs / 60_000);
  if (mins < 1)   return t('admin.justNow');
  if (mins < 60)  return `${mins} ${t('admin.minutesAgo')}`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs} ${t('admin.hoursAgo')}`;
  return `${Math.floor(hrs / 24)} ${t('admin.daysAgo')}`;
}

// ─── CSS Bar Chart ────────────────────────────────────────────────────────────

function BarChart({ data }: { data: MonthlyRevenue[] }) {
  const max = Math.max(...data.map(d => d.revenue), 1);
  return (
    <div className="flex items-end gap-1 h-36 mt-4">
      {data.map((d) => {
        const pct = (d.revenue / max) * 100;
        const monthLabel = d.month.split('-')[1];
        return (
          <div key={d.month} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 hidden group-hover:block bg-slate-800 text-white text-[10px] rounded px-1.5 py-0.5 whitespace-nowrap z-10">
              ৳{d.revenue.toLocaleString()}
            </div>
            <div
              className="w-full bg-emerald-500 hover:bg-emerald-400 rounded-t-sm transition-all min-h-[2px]"
              style={{ height: `${Math.max(pct, 2)}%` }}
            />
            <span className="text-[9px] text-slate-400">{monthLabel}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const [token, setToken] = useState<string | null>(null);
  const [tab,   setTab]   = useState<Tab>('overview');

  const [stats,    setStats]    = useState<Stats | null>(null);
  const [revenue,  setRevenue]  = useState<RevenueData | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);

  // Users state
  const [users,       setUsers]       = useState<AdminUser[]>([]);
  const [userTotal,   setUserTotal]   = useState(0);
  const [userPage,    setUserPage]    = useState(1);
  const [userPages,   setUserPages]   = useState(1);
  const [userSearch,  setUserSearch]  = useState('');
  const [userPlan,    setUserPlan]    = useState('all');
  const [usersLoading, setUsersLoading] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  // ── Auth check ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const tok = localStorage.getItem('token');
    const raw = localStorage.getItem('user');
    if (!tok) { router.push('/login?redirect=/admin'); return; }
    try {
      const u = raw ? JSON.parse(raw) as { is_admin?: boolean } : {};
      if (!u.is_admin) { router.push('/'); return; }
    } catch { router.push('/'); return; }
    setToken(tok);
  }, [router]);

  // ── Load overview data ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    (async () => {
      setLoading(true);
      try {
        const h = { Authorization: `Bearer ${token}` };
        const [sRes, rRes, aRes] = await Promise.all([
          fetch(`${API}/api/admin/stats`,    { headers: h }),
          fetch(`${API}/api/admin/revenue`,  { headers: h }),
          fetch(`${API}/api/admin/activity`, { headers: h }),
        ]);
        if (sRes.status === 403) { router.push('/'); return; }
        setStats(await sRes.json() as Stats);
        setRevenue(await rRes.json() as RevenueData);
        const aData = await aRes.json() as { activities: ActivityItem[] };
        setActivity(aData.activities ?? []);
      } catch {
        setError(t('admin.loadError'));
      } finally {
        setLoading(false);
      }
    })();
  }, [token, router]);

  // ── Load users ───────────────────────────────────────────────────────────────
  const loadUsers = useCallback(async (page: number, search: string, plan: string) => {
    if (!token) return;
    setUsersLoading(true);
    try {
      const params = new URLSearchParams({
        page:  String(page),
        limit: '20',
        ...(search && { search }),
        ...(plan && plan !== 'all' && { plan }),
      });
      const res = await fetch(`${API}/api/admin/users?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json() as UserListResponse;
      setUsers(data.users ?? []);
      setUserTotal(data.total ?? 0);
      setUserPage(data.page ?? 1);
      setUserPages(data.pages ?? 1);
    } catch {
      setError(t('admin.usersLoadError'));
    } finally {
      setUsersLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (tab === 'users' && token) {
      void loadUsers(1, userSearch, userPlan);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, token]);

  // ── User actions ─────────────────────────────────────────────────────────────
  async function patchUser(userId: string, changes: Record<string, unknown>) {
    if (!token) return;
    const res = await fetch(`${API}/api/admin/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(changes),
    });
    if (res.ok) {
      const updated = await res.json() as AdminUser;
      setUsers(prev => prev.map(u => u.id === userId ? updated : u));
    }
  }

  async function deactivateUser(userId: string) {
    if (!token || !confirm(t('admin.confirmDelete'))) return;
    const res = await fetch(`${API}/api/admin/users/${userId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 204) {
      setUsers(prev => prev.filter(u => u.id !== userId));
      setUserTotal(p => p - 1);
    }
  }

  // ── Sidebar tabs ─────────────────────────────────────────────────────────────
  const TABS: { key: Tab; label: string; icon: string }[] = [
    { key: 'overview',  label: t('admin.overview'),  icon: '📊' },
    { key: 'users',     label: t('admin.users'),     icon: '👥' },
    { key: 'revenue',   label: t('admin.revenue'),   icon: '💰' },
    { key: 'activity',  label: t('admin.activity'),  icon: '📋' },
  ];

  if (!token) return null;

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-slate-500 text-sm">{t('admin.loading')}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row">

      {/* ── Desktop sidebar ─────────────────────────────────────────────────── */}
      <aside className="hidden md:flex w-56 bg-gray-900 flex-shrink-0 flex-col min-h-screen">
        <div className="px-4 py-5 border-b border-gray-700">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold text-xs">আ</span>
            </div>
            <div>
              <div className="text-sm font-bold text-white">{t('admin.title')}</div>
              <div className="text-xs text-gray-400">হ্যালো এ্যাডভকেট</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {TABS.map(t2 => (
            <button
              key={t2.key}
              onClick={() => setTab(t2.key)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                tab === t2.key
                  ? 'bg-emerald-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <span>{t2.icon}</span>
              {t2.label}
            </button>
          ))}
        </nav>

        <div className="p-3 border-t border-gray-700">
          <button
            onClick={() => router.push('/')}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <span>🏠</span> {t('admin.backToSite')}
          </button>
        </div>
      </aside>

      {/* ── Mobile top bar ───────────────────────────────────────────────────── */}
      <div className="md:hidden bg-gray-900 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-emerald-600 flex items-center justify-center">
            <span className="text-white font-bold text-xs">আ</span>
          </div>
          <span className="text-white font-bold text-sm">{t('admin.title')}</span>
        </div>
        <button onClick={() => router.push('/')} className="text-gray-400 text-xs">{t('admin.backToSite')}</button>
      </div>

      {/* ── Main content ────────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-auto pb-20 md:pb-0">
        <div className="p-4 md:p-6 max-w-6xl mx-auto">

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>
          )}

          {/* ── OVERVIEW ──────────────────────────────────────────────────── */}
          {tab === 'overview' && stats && (
            <div className="space-y-6">
              <h1 className="text-xl font-bold text-slate-800">{t('admin.platformOverview')}</h1>

              {/* Stats row 1 — Users */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: t('admin.totalUsers'),  value: stats.total_users,        icon: '👥', color: 'text-emerald-700 bg-emerald-50' },
                  { label: t('admin.newToday'),     value: stats.new_users_today,    icon: '🆕', color: 'text-blue-700 bg-blue-50' },
                  { label: t('admin.proUsers'),     value: stats.pro_users,          icon: '⭐', color: 'text-amber-700 bg-amber-50' },
                  { label: t('admin.activeToday'),  value: stats.active_users_today, icon: '🟢', color: 'text-purple-700 bg-purple-50' },
                ].map(card => (
                  <div key={card.label} className="bg-white rounded-2xl border p-5">
                    <div className={`w-9 h-9 rounded-xl ${card.color} flex items-center justify-center text-base mb-3`}>
                      {card.icon}
                    </div>
                    <div className="text-2xl font-bold text-slate-800">{card.value.toLocaleString()}</div>
                    <div className="text-xs text-slate-500 mt-1">{card.label}</div>
                  </div>
                ))}
              </div>

              {/* Stats row 2 — Content */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: t('admin.totalChats'),     value: stats.total_chats,    icon: '💬', color: 'text-emerald-700 bg-emerald-50' },
                  { label: t('admin.chatsToday'),     value: stats.chats_today,    icon: '📨', color: 'text-blue-700 bg-blue-50' },
                  { label: t('admin.documentsCount'), value: stats.total_documents, icon: '📄', color: 'text-purple-700 bg-purple-50' },
                  { label: t('admin.totalCases'),     value: stats.total_cases,    icon: '⚖️', color: 'text-orange-700 bg-orange-50' },
                ].map(card => (
                  <div key={card.label} className="bg-white rounded-2xl border p-5">
                    <div className={`w-9 h-9 rounded-xl ${card.color} flex items-center justify-center text-base mb-3`}>
                      {card.icon}
                    </div>
                    <div className="text-2xl font-bold text-slate-800">{card.value.toLocaleString()}</div>
                    <div className="text-xs text-slate-500 mt-1">{card.label}</div>
                  </div>
                ))}
              </div>

              {/* Revenue summary + Plan distribution */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-white rounded-2xl border p-6">
                  <h2 className="text-base font-bold text-slate-800 mb-4">💰 {t('admin.revenueSummary')}</h2>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-600">{t('admin.totalRevenue')}</span>
                      <span className="font-bold text-emerald-700 text-lg">৳{stats.total_revenue.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-600">{t('admin.mrr')}</span>
                      <span className="font-bold text-blue-700 text-lg">৳{stats.monthly_revenue.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-600">{t('admin.proUsers')}</span>
                      <span className="font-semibold text-amber-700">{stats.pro_users} {t('admin.person')}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-600">{t('admin.activeSubscriptions')}</span>
                      <span className="font-semibold text-slate-700">{stats.active_subscriptions}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-2xl border p-6">
                  <h2 className="text-base font-bold text-slate-800 mb-4">📊 {t('admin.planDistribution')}</h2>
                  <div className="space-y-3">
                    {[
                      { label: t('admin.free'),    count: stats.free_users,    color: 'bg-slate-400' },
                      { label: t('admin.pro'),     count: stats.pro_users,     color: 'bg-amber-400' },
                      { label: t('admin.student'), count: stats.student_users, color: 'bg-blue-400' },
                    ].map(p => {
                      const pct = stats.total_users > 0
                        ? Math.round((p.count / stats.total_users) * 100)
                        : 0;
                      return (
                        <div key={p.label}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-slate-600">{p.label}</span>
                            <span className="font-medium text-slate-800">{p.count} ({pct}%)</span>
                          </div>
                          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                            <div className={`h-full ${p.color} rounded-full`} style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── USERS ─────────────────────────────────────────────────────── */}
          {tab === 'users' && (
            <div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                <h1 className="text-xl font-bold text-slate-800">
                  {t('admin.users')} ({userTotal})
                </h1>
                <div className="flex gap-2">
                  <input
                    value={userSearch}
                    onChange={e => setUserSearch(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && void loadUsers(1, userSearch, userPlan)}
                    placeholder={t('admin.searchUsers')}
                    className="border rounded-xl px-3 py-2 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                  />
                  <select
                    value={userPlan}
                    onChange={e => { setUserPlan(e.target.value); void loadUsers(1, userSearch, e.target.value); }}
                    className="border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                  >
                    <option value="all">{t('admin.allPlans')}</option>
                    <option value="free">{t('admin.free')}</option>
                    <option value="pro">{t('admin.pro')}</option>
                    <option value="student">{t('admin.student')}</option>
                  </select>
                  <button
                    onClick={() => void loadUsers(1, userSearch, userPlan)}
                    className="px-3 py-2 bg-emerald-600 text-white rounded-xl text-sm hover:bg-emerald-700 transition-colors"
                  >
                    🔍
                  </button>
                </div>
              </div>

              {/* Desktop table */}
              <div className="bg-white rounded-2xl border overflow-hidden hidden md:block">
                {usersLoading ? (
                  <div className="py-10 text-center text-slate-400 text-sm">{t('admin.loading')}</div>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 border-b">
                      <tr>
                        <th className="text-left px-4 py-3 text-slate-500 font-medium">নাম / ইমেইল</th>
                        <th className="text-left px-4 py-3 text-slate-500 font-medium">প্ল্যান</th>
                        <th className="text-center px-4 py-3 text-slate-500 font-medium">চ্যাট</th>
                        <th className="text-center px-4 py-3 text-slate-500 font-medium">যোগদান</th>
                        <th className="text-center px-4 py-3 text-slate-500 font-medium">{t('admin.adminToggle')}</th>
                        <th className="text-center px-4 py-3 text-slate-500 font-medium">অ্যাকশন</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {users.map(u => (
                        <tr key={u.id} className="hover:bg-slate-50">
                          <td className="px-4 py-3">
                            <div className="font-medium text-slate-800">{u.name || '—'}</div>
                            <div className="text-xs text-slate-400">{u.email}</div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5">
                              {planBadge(u.plan)}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-center text-slate-600 text-xs">{u.total_chats}</td>
                          <td className="px-4 py-3 text-center text-slate-500 text-xs">
                            {u.created_at ? new Date(u.created_at).toLocaleDateString('bn-BD') : '—'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Toggle
                              checked={u.is_admin}
                              disabled={u.is_admin}
                              onChange={() => patchUser(u.id, { is_admin: !u.is_admin })}
                            />
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-center gap-1">
                              {u.plan === 'free' ? (
                                <button
                                  onClick={() => patchUser(u.id, { plan: 'pro' })}
                                  className="px-2 py-1 text-xs bg-amber-100 text-amber-800 rounded-lg hover:bg-amber-200 transition-colors"
                                >
                                  {t('admin.makeProBtn')}
                                </button>
                              ) : u.plan === 'pro' ? (
                                <button
                                  onClick={() => patchUser(u.id, { plan: 'free' })}
                                  className="px-2 py-1 text-xs bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
                                >
                                  {t('admin.makeFreeBtn')}
                                </button>
                              ) : (
                                <button
                                  onClick={() => patchUser(u.id, { plan: 'free' })}
                                  className="px-2 py-1 text-xs bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
                                >
                                  {t('admin.makeFreeBtn')}
                                </button>
                              )}
                              {!u.is_admin && (
                                <button
                                  onClick={() => deactivateUser(u.id)}
                                  className="px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                >
                                  {t('admin.deleteUser')}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {!usersLoading && users.length === 0 && (
                  <div className="py-10 text-center text-slate-400 text-sm">{t('admin.noUsers')}</div>
                )}
              </div>

              {/* Mobile cards */}
              <div className="md:hidden space-y-3">
                {usersLoading ? (
                  <div className="py-10 text-center text-slate-400 text-sm">{t('admin.loading')}</div>
                ) : users.map(u => (
                  <div key={u.id} className="bg-white rounded-2xl border p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="font-medium text-slate-800 text-sm">{u.name || u.email}</div>
                        <div className="text-xs text-slate-400">{u.email}</div>
                      </div>
                      {planBadge(u.plan)}
                    </div>
                    <div className="flex items-center gap-2 mt-3">
                      {u.plan !== 'pro' && (
                        <button
                          onClick={() => patchUser(u.id, { plan: 'pro' })}
                          className="flex-1 py-1.5 text-xs bg-amber-100 text-amber-800 rounded-lg font-medium"
                        >
                          {t('admin.makeProBtn')}
                        </button>
                      )}
                      {u.plan !== 'free' && (
                        <button
                          onClick={() => patchUser(u.id, { plan: 'free' })}
                          className="flex-1 py-1.5 text-xs bg-slate-100 text-slate-600 rounded-lg font-medium"
                        >
                          {t('admin.makeFreeBtn')}
                        </button>
                      )}
                      {!u.is_admin && (
                        <button
                          onClick={() => deactivateUser(u.id)}
                          className="py-1.5 px-3 text-xs text-red-600 border border-red-200 rounded-lg"
                        >
                          {t('admin.deleteUser')}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {userPages > 1 && (
                <div className="flex items-center justify-center gap-2 mt-4">
                  <button
                    disabled={userPage <= 1}
                    onClick={() => { const p = userPage - 1; setUserPage(p); void loadUsers(p, userSearch, userPlan); }}
                    className="px-3 py-1.5 text-sm border rounded-lg hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    ← আগে
                  </button>
                  <span className="text-sm text-slate-600">{userPage} / {userPages}</span>
                  <button
                    disabled={userPage >= userPages}
                    onClick={() => { const p = userPage + 1; setUserPage(p); void loadUsers(p, userSearch, userPlan); }}
                    className="px-3 py-1.5 text-sm border rounded-lg hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    পরে →
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ── REVENUE ───────────────────────────────────────────────────── */}
          {tab === 'revenue' && revenue && (
            <div className="space-y-6">
              <h1 className="text-xl font-bold text-slate-800">💰 রাজস্ব বিশ্লেষণ</h1>

              {/* Summary cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { label: t('admin.revenueTotal'), value: `৳${revenue.total_revenue.toLocaleString()}`, color: 'text-emerald-700 bg-emerald-50' },
                  { label: t('admin.currentMRR'),   value: `৳${revenue.mrr.toLocaleString()}`,           color: 'text-blue-700 bg-blue-50' },
                  { label: 'গড় প্রতি গ্রাহক',      value: stats && stats.pro_users > 0
                    ? `৳${Math.round(revenue.total_revenue / stats.pro_users).toLocaleString()}`
                    : '৳০', color: 'text-purple-700 bg-purple-50' },
                ].map(c => (
                  <div key={c.label} className="bg-white rounded-2xl border p-6">
                    <div className={`text-3xl font-bold mb-1 ${c.color.split(' ')[0]}`}>{c.value}</div>
                    <div className="text-sm text-slate-500">{c.label}</div>
                  </div>
                ))}
              </div>

              {/* Bar chart */}
              <div className="bg-white rounded-2xl border p-6">
                <h2 className="text-base font-bold text-slate-800 mb-1">{t('admin.monthlyChart')}</h2>
                <p className="text-xs text-slate-400 mb-2">হোভার করুন রাজস্ব দেখতে</p>
                <BarChart data={revenue.monthly} />
              </div>

              {/* Monthly table */}
              <div className="bg-white rounded-2xl border overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 border-b">
                    <tr>
                      <th className="text-left px-4 py-3 text-slate-500 font-medium">মাস</th>
                      <th className="text-right px-4 py-3 text-slate-500 font-medium">নতুন প্রো</th>
                      <th className="text-right px-4 py-3 text-slate-500 font-medium">রাজস্ব</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {[...revenue.monthly].reverse().map(m => (
                      <tr key={m.month} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-slate-700 font-medium">{m.month}</td>
                        <td className="px-4 py-3 text-right text-slate-600">{m.new_pro}</td>
                        <td className="px-4 py-3 text-right font-semibold text-emerald-700">
                          {m.revenue > 0 ? `৳${m.revenue.toLocaleString()}` : <span className="text-slate-300">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── ACTIVITY ──────────────────────────────────────────────────── */}
          {tab === 'activity' && (
            <div>
              <h1 className="text-xl font-bold text-slate-800 mb-4">📋 সাম্প্রতিক কার্যকলাপ</h1>
              <div className="bg-white rounded-2xl border p-6">
                {activity.length === 0 ? (
                  <p className="text-center text-slate-400 py-10 text-sm">{t('admin.noActivity')}</p>
                ) : (
                  <div className="space-y-4">
                    {activity.map((a, i) => {
                      const iconMap: Record<string, string> = {
                        new_user:    '👤',
                        new_payment: '💳',
                        new_chat:    '💬',
                        new_document:'📄',
                      };
                      const colorMap: Record<string, string> = {
                        new_user:    'bg-blue-100 text-blue-700',
                        new_payment: 'bg-emerald-100 text-emerald-700',
                        new_chat:    'bg-purple-100 text-purple-700',
                        new_document:'bg-orange-100 text-orange-700',
                      };
                      return (
                        <div key={i} className="flex items-start gap-3">
                          <div className={`w-9 h-9 rounded-full flex items-center justify-center text-base flex-shrink-0 ${colorMap[a.type] ?? 'bg-slate-100 text-slate-600'}`}>
                            {iconMap[a.type] ?? '•'}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-slate-800">{a.description}</p>
                            {a.detail && <p className="text-xs text-slate-500 mt-0.5">{a.detail}</p>}
                          </div>
                          <span className="text-xs text-slate-400 flex-shrink-0 mt-0.5">{timeAgo(a.time)}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ── Mobile bottom tab bar ────────────────────────────────────────────── */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t flex z-30">
        {TABS.map(t2 => (
          <button
            key={t2.key}
            onClick={() => setTab(t2.key)}
            className={`flex-1 flex flex-col items-center py-2 text-xs gap-0.5 transition-colors ${
              tab === t2.key ? 'text-emerald-600' : 'text-slate-500'
            }`}
          >
            <span className="text-lg leading-none">{t2.icon}</span>
            <span className="leading-none">{t2.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
