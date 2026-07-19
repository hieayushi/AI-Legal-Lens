"use client";
import { useEffect, useState } from "react";
import { evalApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { FlaskConical } from "lucide-react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

const METHOD_COLORS: Record<string, string> = {
  hierarchical: "#1e40af",
  bm25: "#6b7280",
  hybrid: "#7c3aed",
};

export default function EvaluationPage() {
  const { ready } = useAuth();
  const [comparison, setComparison] = useState<Record<string, any>>({});
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    Promise.all([
      evalApi.compare().catch(() => ({ data: {} })),
      evalApi.listRuns().catch(() => ({ data: [] })),
    ])
      .then(([c, r]) => {
        setComparison(c.data || {});
        setRuns(r.data || []);
      })
      .finally(() => setLoading(false));
  }, [ready]);

  if (!ready) return null;

  const hasData = Object.keys(comparison).length > 0;

  const radarData = [
    {
      metric: "Precision",
      ...Object.fromEntries(
        Object.entries(comparison).map(([k, v]) => [
          k,
          +(v.avg_precision * 100).toFixed(1),
        ])
      ),
    },
    {
      metric: "Recall",
      ...Object.fromEntries(
        Object.entries(comparison).map(([k, v]) => [
          k,
          +(v.avg_recall * 100).toFixed(1),
        ])
      ),
    },
    {
      metric: "F1",
      ...Object.fromEntries(
        Object.entries(comparison).map(([k, v]) => [
          k,
          +(v.avg_f1 * 100).toFixed(1),
        ])
      ),
    },
    {
      metric: "Citation Acc.",
      ...Object.fromEntries(
        Object.entries(comparison).map(([k, v]) => [
          k,
          +(v.avg_citation_accuracy * 100).toFixed(1),
        ])
      ),
    },
  ];

  const latencyData = Object.entries(comparison).map(([method, v]) => ({
    method: method.charAt(0).toUpperCase() + method.slice(1),
    latency: Math.round(v.avg_latency_ms),
  }));

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <FlaskConical className="w-5 h-5 text-violet-600" />
          <h1 className="text-xl sm:text-2xl font-display font-semibold text-ink">
            Evaluation Dashboard
          </h1>
        </div>
        <p className="text-sm text-ink-muted">
          Comparing BM25 · Hybrid · Hierarchical Page Indexing across precision,
          recall, and citation accuracy
        </p>
      </div>

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card skeleton h-40" />
          ))}
        </div>
      )}

      {!loading && !hasData && (
        <div className="card text-center py-16">
          <FlaskConical className="w-12 h-12 text-ink-muted mx-auto mb-3 opacity-30" />
          <p className="text-sm text-ink-muted">No evaluation runs yet.</p>
          <p className="text-xs text-ink-muted mt-1">
            Trigger a run via the API:
          </p>
          <code className="text-xs bg-parchment-warm border border-parchment-border rounded px-2 py-1 mt-2 inline-block">
            POST /api/v1/eval/run
          </code>
        </div>
      )}

      {!loading && hasData && (
        <>
          {/* Method comparison cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {Object.entries(comparison).map(([method, metrics]) => (
              <div
                key={method}
                className="card border-t-4"
                style={{ borderTopColor: METHOD_COLORS[method] || "#6b7280" }}
              >
                <h3 className="font-medium text-sm capitalize text-ink mb-3">
                  {method}
                </h3>
                <div className="grid grid-cols-2 gap-3 text-center">
                  <Metric
                    label="Precision"
                    value={`${(metrics.avg_precision * 100).toFixed(1)}%`}
                  />
                  <Metric
                    label="Recall"
                    value={`${(metrics.avg_recall * 100).toFixed(1)}%`}
                  />
                  <Metric
                    label="F1"
                    value={`${(metrics.avg_f1 * 100).toFixed(1)}%`}
                  />
                  <Metric
                    label="Citation Acc."
                    value={`${(metrics.avg_citation_accuracy * 100).toFixed(1)}%`}
                  />
                </div>
                <div className="section-divider" />
                <div className="flex justify-between text-xs text-ink-muted">
                  <span>Latency: {Math.round(metrics.avg_latency_ms)}ms</span>
                  <span
                    className={
                      metrics.hallucination_rate > 0.1
                        ? "text-verdict-red"
                        : "text-verdict-green"
                    }
                  >
                    Hallucination: {(metrics.hallucination_rate * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            <div className="card">
              <h2 className="font-medium text-sm text-ink mb-4">
                Multi-Metric Comparison
              </h2>
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#e5e0d8" />
                  <PolarAngleAxis
                    dataKey="metric"
                    tick={{ fontSize: 11, fill: "#6b7280" }}
                  />
                  {Object.keys(comparison).map((method) => (
                    <Radar
                      key={method}
                      name={method}
                      dataKey={method}
                      stroke={METHOD_COLORS[method] || "#6b7280"}
                      fill={METHOD_COLORS[method] || "#6b7280"}
                      fillOpacity={0.1}
                      strokeWidth={2}
                    />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      fontSize: 11,
                      borderRadius: 8,
                      border: "1px solid #e5e0d8",
                    }}
                    formatter={(v: any) => [`${v}%`]}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <h2 className="font-medium text-sm text-ink mb-4">
                Average Latency (ms)
              </h2>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={latencyData} barSize={48}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#e5e0d8"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="method"
                    tick={{ fontSize: 12, fill: "#6b7280" }}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#6b7280" }}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: 11,
                      borderRadius: 8,
                      border: "1px solid #e5e0d8",
                    }}
                    formatter={(v: any) => [`${v}ms`]}
                  />
                  <Bar dataKey="latency" radius={[6, 6, 0, 0]} fill="#1e40af" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {/* Run history table */}
      {!loading && runs.length > 0 && (
        <div className="card">
          <h2 className="font-medium text-sm text-ink mb-3">Evaluation Runs</h2>
            <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-parchment-border text-left text-ink-muted">
                  <th className="pb-2 font-medium">Method</th>
                  <th className="pb-2 font-medium">Questions</th>
                  <th className="pb-2 font-medium">Precision</th>
                  <th className="pb-2 font-medium">Recall</th>
                  <th className="pb-2 font-medium">F1</th>
                  <th className="pb-2 font-medium">Latency</th>
                  <th className="pb-2 font-medium">Hallucination</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    key={run.run_id}
                    className="border-b border-parchment-border last:border-0"
                  >
                    <td
                      className="py-2 capitalize font-medium"
                      style={{
                        color:
                          METHOD_COLORS[run.retrieval_method] || "#6b7280",
                      }}
                    >
                      {run.retrieval_method}
                    </td>
                    <td className="py-2 text-ink-soft">{run.total_questions}</td>
                    <td className="py-2">
                      {(run.avg_precision * 100).toFixed(1)}%
                    </td>
                    <td className="py-2">
                      {(run.avg_recall * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 font-medium">
                      {(run.avg_f1 * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 text-ink-soft">
                      {Math.round(run.avg_latency_ms)}ms
                    </td>
                    <td className="py-2">
                      <span
                        className={
                          run.hallucination_rate > 0.1
                            ? "text-verdict-red"
                            : "text-verdict-green"
                        }
                      >
                        {(run.hallucination_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] text-ink-muted">{label}</div>
      <div className="text-base font-semibold text-ink">{value}</div>
    </div>
  );
}
