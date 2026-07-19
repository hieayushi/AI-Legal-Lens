"use client";
import { useEffect, useState } from "react";
import { analyticsApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { BarChart2 } from "lucide-react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

export default function AnalyticsPage() {
  const { ready } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    setLoading(true);
    analyticsApi.summary(days)
      .then((r) => setStats(r.data))
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, [ready, days]);

  if (!ready) return null;

  const methodData = Object.entries(stats?.retrieval_method_distribution || {}).map(
    ([method, count]) => ({ method: method.charAt(0).toUpperCase() + method.slice(1), count })
  );

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-5 h-5 text-brand" />
          <h1 className="text-xl sm:text-2xl font-display font-semibold text-ink">Analytics</h1>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="input w-full sm:w-36 text-sm"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="card skeleton h-20" />)}
        </div>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {[
              { label: "Total Documents", value: stats?.total_documents ?? 0 },
              { label: `Queries (${days}d)`, value: stats?.total_queries ?? 0 },
              { label: "Avg Latency", value: `${Math.round(stats?.avg_latency_ms ?? 0)}ms` },
              { label: "Top Document Queries", value: stats?.top_queried_documents?.length ?? 0 },
            ].map((s) => (
              <div key={s.label} className="card">
                <p className="text-xs text-ink-muted mb-1">{s.label}</p>
                <p className="text-2xl font-display font-semibold text-ink">{s.value}</p>
              </div>
            ))}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card">
              <h2 className="font-medium text-sm text-ink mb-4">Daily Query Volume</h2>
              {stats?.query_volume_by_day?.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={stats.query_volume_by_day}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e0d8" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e0d8" }} />
                    <Line type="monotone" dataKey="count" stroke="#1e40af" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : <p className="text-sm text-ink-muted py-10 text-center">No data yet</p>}
            </div>

            <div className="card">
              <h2 className="font-medium text-sm text-ink mb-4">Retrieval Method Usage</h2>
              {methodData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={methodData} barSize={40}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e0d8" vertical={false} />
                    <XAxis dataKey="method" tick={{ fontSize: 11 }} axisLine={false} />
                    <YAxis tick={{ fontSize: 10 }} axisLine={false} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e0d8" }} />
                    <Bar dataKey="count" fill="#1e40af" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <p className="text-sm text-ink-muted py-10 text-center">No data yet</p>}
            </div>
          </div>

          {/* Top documents table */}
          {stats?.top_queried_documents?.length > 0 && (
            <div className="card mt-4">
              <h2 className="font-medium text-sm text-ink mb-3">Top Queried Documents</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-parchment-border text-left">
                    <th className="pb-2 text-xs text-ink-muted font-medium">Document</th>
                    <th className="pb-2 text-xs text-ink-muted font-medium text-right">Queries</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.top_queried_documents.map((d: any, i: number) => (
                    <tr key={i} className="border-b border-parchment-border last:border-0">
                      <td className="py-2 text-ink">{d.title}</td>
                      <td className="py-2 text-ink-soft text-right">{d.query_count}</td>
                    </tr>
                  ))}
                </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
