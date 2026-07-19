"use client";
import { useState, useEffect } from "react";
import { docsApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { Building2, Search, FileText } from "lucide-react";
import Link from "next/link";

const GOV_TYPES = ["policy", "circular", "regulation", "order", "compliance", "tender"];

export default function GovernancePage() {
  const { ready } = useAuth();
  const [documents, setDocuments] = useState<any[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    // Fetch all governance-related doc types
    Promise.all(GOV_TYPES.map((t) => docsApi.list(t).catch(() => ({ data: [] }))))
      .then((results) => {
        const all = results.flatMap((r) => r.data || []);
        const unique = Array.from(new Map(all.map((d) => [d.id, d])).values());
        setDocuments(unique);
      })
      .finally(() => setLoading(false));
  }, [ready]);

  if (!ready) return null;

  const filtered = query.trim()
    ? documents.filter((d) =>
        d.title?.toLowerCase().includes(query.toLowerCase()) ||
        d.tags?.some((t: string) => t.toLowerCase().includes(query.toLowerCase()))
      )
    : documents;

  const grouped = GOV_TYPES.reduce((acc, type) => {
    const docs = filtered.filter((d) => d.doc_type === type);
    if (docs.length > 0) acc[type] = docs;
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">
      <div className="mb-6 flex items-start sm:items-center gap-2">
        <Building2 className="w-5 h-5 sm:w-6 sm:h-6 text-brand flex-shrink-0 mt-0.5 sm:mt-0" />
        <div>
          <h1 className="text-xl sm:text-2xl font-display font-semibold text-ink">Governance Intelligence</h1>
          <p className="text-xs sm:text-sm text-ink-muted">Policies, circulars, regulations, and government orders</p>
        </div>
      </div>

      <div className="relative mb-5">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search governance documents..."
          className="input pl-9"
        />
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="card skeleton h-20" />)}
        </div>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="card text-center py-16">
          <Building2 className="w-12 h-12 text-ink-muted mx-auto mb-3 opacity-30" />
          <p className="text-sm text-ink-muted">No governance documents uploaded yet.</p>
          <Link href="/upload" className="btn-primary mt-3 inline-block text-sm">Upload Document</Link>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([type, docs]) => (
            <div key={type}>
              <h2 className="text-sm font-semibold text-ink-soft capitalize mb-2 uppercase tracking-wide">
                {type}s ({docs.length})
              </h2>
              <div className="space-y-2">
                {docs.map((doc) => (
                  <div key={doc.id} className="card-hover flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <FileText className="w-4 h-4 text-brand flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-ink truncate">{doc.title}</p>
                        <p className="text-xs text-ink-muted">{doc.page_count} pages · {doc.processing_status}</p>
                      </div>
                    </div>
                    {doc.processing_status === "indexed" && (
                      <Link href={`/query?doc=${doc.id}`} className="btn-secondary text-xs flex-shrink-0">
                        Query
                      </Link>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
