"use client";
import { useState, useEffect } from "react";
import { docsApi, queryApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { Search, FileText, Calendar, Tag, Loader2 } from "lucide-react";
import Link from "next/link";
import { clsx } from "clsx";

const DOC_TYPES = ["all", "judgment", "policy", "circular", "regulation", "order", "compliance", "tender"];

export default function SearchPage() {
  const { ready } = useAuth();
  const [query, setQuery] = useState("");
  const [docType, setDocType] = useState("all");
  const [documents, setDocuments] = useState<any[]>([]);
  const [filtered, setFiltered] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    docsApi.list()
      .then((r) => { setDocuments(r.data); setFiltered(r.data); })
      .finally(() => setLoading(false));
  }, [ready]);

  useEffect(() => {
    let results = documents;
    if (docType !== "all") results = results.filter((d) => d.doc_type === docType);
    if (query.trim()) {
      const q = query.toLowerCase();
      results = results.filter(
        (d) =>
          d.title?.toLowerCase().includes(q) ||
          d.case_number?.toLowerCase().includes(q) ||
          d.court_name?.toLowerCase().includes(q) ||
          d.tags?.some((t: string) => t.toLowerCase().includes(q))
      );
    }
    setFiltered(results);
  }, [query, docType, documents]);

  if (!ready) return null;

  const statusColor: Record<string, string> = {
    indexed: "badge-green", processing: "badge-amber",
    failed: "badge-red", pending: "badge-blue",
  };

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-display font-semibold text-ink">Case Search</h1>
        <p className="text-sm text-ink-muted mt-0.5">Browse and search all indexed legal documents</p>
      </div>

      {/* Filters */}
      <div className="card mb-5">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by title, case number, court name, tags..."
              className="input pl-9"
            />
          </div>
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="input sm:w-48"
          >
            {DOC_TYPES.map((t) => (
              <option key={t} value={t}>{t === "all" ? "All Types" : t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>
        <p className="text-xs text-ink-muted mt-2">{filtered.length} document{filtered.length !== 1 ? "s" : ""} found</p>
      </div>

      {/* Results */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <div key={i} className="card skeleton h-24" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-16">
          <FileText className="w-12 h-12 text-ink-muted mx-auto mb-3 opacity-30" />
          <p className="text-sm text-ink-muted">
            {documents.length === 0 ? "No documents uploaded yet." : "No documents match your search."}
          </p>
          {documents.length === 0 && (
            <Link href="/upload" className="btn-primary mt-3 inline-block text-sm">Upload a Document</Link>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((doc) => (
            <div key={doc.id} className="card-hover">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 sm:gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <h3 className="font-medium text-sm text-ink truncate">{doc.title}</h3>
                    <span className={statusColor[doc.processing_status] || "badge-blue"}>
                      {doc.processing_status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 sm:gap-4 text-xs text-ink-muted flex-wrap">
                    {doc.court_name && <span>{doc.court_name}</span>}
                    {doc.case_number && <span className="font-mono">{doc.case_number}</span>}
                    {doc.judgment_date && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />{doc.judgment_date}
                      </span>
                    )}
                    <span>{doc.page_count} pages</span>
                  </div>
                  {doc.tags?.length > 0 && (
                    <div className="flex items-center gap-1 mt-2 flex-wrap">
                      <Tag className="w-3 h-3 text-ink-muted" />
                      {doc.tags.map((tag: string) => (
                        <span key={tag} className="badge badge-blue">{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex flex-row sm:flex-col gap-2 flex-shrink-0">
                  <span className="badge badge-blue capitalize">{doc.doc_type}</span>
                  {doc.processing_status === "indexed" && (
                    <Link
                      href={`/query?doc=${doc.id}`}
                      className="text-xs text-brand hover:underline sm:text-right"
                    >
                      Query →
                    </Link>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
