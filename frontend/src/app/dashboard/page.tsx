"use client";
import { useEffect, useState } from "react";
import { analyticsApi, queryApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { FileText, MessageSquare, Clock, TrendingUp } from "lucide-react";
import Link from "next/link";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";

export default function DashboardPage() {
  const { ready } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    Promise.all([
      analyticsApi.summary(30).catch(() => ({ data: null })),
      queryApi.history(5).catch(() => ({ data: [] })),
    ]).then(([s, h]) => {
      setStats(s.data);
      setHistory(h.data || []);
    }).finally(() => setLoading(false));
  }, [ready]);

  if (!ready || loading) return <DashboardSkeleton />;

  const methodColors: Record<string, string> = {
    hierarchical: "#1e40af",
    bm25: "#6b7280",
    hybrid: "#7c3aed",
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-ink">Dashboard</h1>
        <p className="text-sm text-ink-muted mt-0.5">Judicial intelligence at a glance</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Documents Indexed" value={stats?.total_documents ?? 0}
          icon={<FileText className="w-5 h-5 text-brand" />} color="blue" />
        <StatCard label="Queries (30d)" value={stats?.total_queries ?? 0}
          icon={<MessageSquare className="w-5 h-5 text-violet-600" />} color="violet" />
        <StatCard label="Avg Latency" value={`${Math.round(stats?.avg_latency_ms ?? 0)}ms`}
          icon={<Clock className="w-5 h-5 text-amber-600" />} color="amber" />
        <StatCard label="Active Methods"
          value={Object.keys(stats?.retrieval_method_distribution ?? {}).length || 0}
          icon={<TrendingUp className="w-5 h-5 text-green-700" />} color="green" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="card lg:col-span-2">
          <h2 className="font-medium text-sm text-ink mb-4">Query Volume (30 days)</h2>
          {stats?.query_volume_by_day?.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={stats.query_volume_by_day}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e0d8" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#6b7280" }}
                  tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10, fill: "#6b7280" }} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e0d8" }} />
                <Line type="monotone" dataKey="count" stroke="#1e40af" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[180px] flex items-center justify-center text-sm text-ink-muted">
              No query data yet. Ask your first question →{" "}
              <Link href="/query" className="text-brand ml-1 hover:underline">Ask LegalLens</Link>
            </div>
          )}
        </div>

        <div className="card">
          <h2 className="font-medium text-sm text-ink mb-4">Retrieval Methods</h2>
          {Object.keys(stats?.retrieval_method_distribution ?? {}).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(stats.retrieval_method_distribution).map(([method, count]) => {
                const total = Object.values(stats.retrieval_method_distribution)
                  .reduce((a: number, b) => a + (b as number), 0);
                const pct = total > 0 ? Math.round(((count as number) / total) * 100) : 0;
                return (
                  <div key={method}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="capitalize text-ink-soft">{method}</span>
                      <span className="text-ink font-medium">{pct}%</span>
                    </div>
                    <div className="h-1.5 bg-parchment-warm rounded-full overflow-hidden">
                      <div className="h-full rounded-full"
                        style={{ width: `${pct}%`, backgroundColor: methodColors[method] || "#6b7280" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-ink-muted mt-2">No queries yet</p>
          )}
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="font-medium text-sm text-ink mb-3">Top Queried Documents</h2>
          {stats?.top_queried_documents?.length > 0 ? (
            <div className="space-y-2">
              {stats.top_queried_documents.map((d: any, i: number) => (
                <div key={i} className="flex items-center justify-between py-1.5 border-b border-parchment-border last:border-0">
                  <span className="text-sm text-ink truncate flex-1">{d.title}</span>
                  <span className="text-xs text-ink-muted ml-2">{d.query_count} queries</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center">
              <p className="text-sm text-ink-muted">No documents queried yet.</p>
              <Link href="/upload" className="text-xs text-brand mt-1 block hover:underline">
                Upload a document to get started
              </Link>
            </div>
          )}
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-medium text-sm text-ink">Recent Queries</h2>
            <Link href="/query" className="text-xs text-brand hover:underline">New query</Link>
          </div>
          {history.length > 0 ? (
            <div className="space-y-2">
              {history.map((q: any) => (
                <div key={q.id} className="py-1.5 border-b border-parchment-border last:border-0">
                  <p className="text-sm text-ink truncate">{q.query_text}</p>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="text-[10px] text-ink-muted capitalize">{q.retrieval_method}</span>
                    <span className="text-[10px] text-ink-muted">{q.latency_ms}ms</span>
                    <span className="text-[10px] text-ink-muted">{q.citation_count} citations</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center">
              <p className="text-sm text-ink-muted">No queries yet.</p>
              <Link href="/query" className="text-xs text-brand mt-1 block hover:underline">
                Ask your first question
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color }: any) {
  const bg: Record<string, string> = {
    blue: "bg-brand-light", violet: "bg-violet-50",
    amber: "bg-amber-50", green: "bg-green-50",
  };
  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-ink-muted mb-1">{label}</p>
          <p className="text-2xl font-display font-semibold text-ink">{value}</p>
        </div>
        <div className={`w-9 h-9 rounded-lg ${bg[color] || "bg-parchment-warm"} flex items-center justify-center flex-shrink-0`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="skeleton h-7 w-40 mb-6" />
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card"><div className="skeleton h-16 w-full" /></div>
        ))}
      </div>
      <div className="skeleton h-48 w-full rounded-xl" />
    </div>
  );
}
