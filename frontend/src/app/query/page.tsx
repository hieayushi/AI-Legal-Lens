"use client";
import { useState, useEffect, useRef } from "react";
import { queryApi, docsApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { Send, Scale, FileText, Star, AlertCircle, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { clsx } from "clsx";

type Citation = {
  document_id: string;
  document_title: string;
  section_title: string | null;
  page_number: number;
  evidence_text: string;
  confidence_score: number;
  retrieval_rank: number;
};

type QueryResult = {
  query_id: string;
  answer: string;
  citations: Citation[];
  retrieval_method: string;
  model_used: string;
  latency_ms: number;
  warning?: string;
};

export default function QueryPage() {
  const { ready } = useAuth();
  const [query, setQuery] = useState("");
  const [method, setMethod] = useState("hierarchical");
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<number | null>(null);
  const [activeCitationTab, setActiveCitationTab] = useState<number>(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!ready) return;
    docsApi.list().then((r) => setDocuments(r.data)).catch(() => {});
  }, [ready]);

  if (!ready) return null;

  const handleSubmit = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setResult(null);
    setFeedback(null);
    setActiveCitationTab(0);
    try {
      const r = await queryApi.ask(query, selectedDocs, method, 5);
      setResult(r.data);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Query failed");
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (score: number) => {
    if (!result) return;
    try {
      await queryApi.feedback(result.query_id, score);
      setFeedback(score);
      toast.success("Feedback recorded");
    } catch {}
  };

  const confidenceColor = (score: number) => {
    if (score >= 0.7) return "text-verdict-green";
    if (score >= 0.4) return "text-verdict-amber";
    return "text-verdict-red";
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-parchment-border bg-white">
        <div className="flex items-center gap-2">
          <Scale className="w-5 h-5 text-brand" />
          <h1 className="font-display font-semibold text-ink">Ask LegalLens</h1>
        </div>
        <p className="text-xs text-ink-muted mt-0.5">
          Hierarchical page retrieval · Every answer cites exact pages
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5 max-w-5xl mx-auto w-full">
        {/* Query controls */}
        <div className="card mb-5">
          {/* Method selector */}
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <span className="text-xs text-ink-muted">Retrieval method:</span>
            {["hierarchical", "bm25", "hybrid"].map((m) => (
              <button
                key={m}
                onClick={() => setMethod(m)}
                className={clsx(
                  "px-3 py-1 rounded-full text-xs font-medium transition-colors",
                  method === m
                    ? "bg-brand text-white"
                    : "bg-parchment-warm text-ink-soft hover:bg-parchment-border"
                )}
              >
                {m === "hierarchical" ? "Hierarchical (recommended)" : m.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Document scope */}
          <div className="mb-4">
            <label className="text-xs text-ink-muted block mb-1.5">
              Scope to documents (optional — leave empty to search all)
            </label>
            <div className="flex flex-wrap gap-2">
              {documents
                .filter((d) => d.processing_status === "indexed")
                .map((doc) => (
                  <button
                    key={doc.id}
                    onClick={() =>
                      setSelectedDocs((prev) =>
                        prev.includes(doc.id)
                          ? prev.filter((id) => id !== doc.id)
                          : [...prev, doc.id]
                      )
                    }
                    className={clsx(
                      "flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border transition-colors",
                      selectedDocs.includes(doc.id)
                        ? "bg-brand-light border-brand text-brand"
                        : "bg-white border-parchment-border text-ink-soft hover:border-brand/50"
                    )}
                  >
                    <FileText className="w-3 h-3" />
                    <span className="max-w-[140px] truncate">{doc.title}</span>
                  </button>
                ))}
              {documents.filter((d) => d.processing_status === "indexed").length === 0 && (
                <span className="text-xs text-ink-muted">
                  No indexed documents yet. Upload a PDF first.
                </span>
              )}
            </div>
          </div>

          {/* Query input */}
          <div className="relative">
            <textarea
              ref={textareaRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
              }}
              placeholder={`e.g. "Why was anticipatory bail denied?" or "What are the eligibility criteria?"`}
              rows={3}
              className="input resize-none pr-28"
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !query.trim()}
              className="absolute right-3 bottom-3 btn-primary px-3 py-1.5 flex items-center gap-1.5"
            >
              {loading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
              {loading ? "Thinking..." : "Ask"}
            </button>
          </div>
          <p className="text-[10px] text-ink-muted mt-1.5">Ctrl+Enter to submit</p>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="card text-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-brand mx-auto mb-3" />
            <p className="text-sm text-ink-muted">Retrieving pages and generating answer...</p>
            <p className="text-xs text-ink-muted mt-1">
              This may take 10–30 seconds
            </p>
          </div>
        )}

        {/* Result */}
        {result && !loading && (
          <div className="space-y-4">
            {/* Warning */}
            {result.warning && (
              <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3">
                <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-verdict-amber">{result.warning}</p>
              </div>
            )}

            {/* Answer */}
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-medium text-sm text-ink">Answer</h2>
                <div className="flex items-center gap-3 text-[10px] text-ink-muted">
                 
                <span>{result.latency_ms}ms</span>
                  <span className="capitalize">{result.retrieval_method}</span>
                </div>
              </div>
              <p className="text-sm text-ink leading-relaxed whitespace-pre-wrap">
                {result.answer}
              </p>

              {/* Star feedback */}
              <div className="flex items-center gap-2 mt-4 pt-3 border-t border-parchment-border">
                <span className="text-xs text-ink-muted">Was this helpful?</span>
                {[1, 2, 3, 4, 5].map((score) => (
                  <button
                    key={score}
                    onClick={() => handleFeedback(score)}
                    className={clsx(
                      "transition-colors",
                      feedback !== null && score <= feedback
                        ? "text-amber-400"
                        : "text-ink-muted hover:text-amber-400"
                    )}
                  >
                    <Star
                      className="w-4 h-4"
                      fill={
                        feedback !== null && score <= feedback ? "currentColor" : "none"
                      }
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Citations */}
            {result.citations.length > 0 && (
              <div>
                <h2 className="font-medium text-sm text-ink mb-3">
                  Citations ({result.citations.length})
                </h2>
                
                {/* Horizontal Citation Tabs */}
                <div className="flex border-b border-parchment-border mb-4 overflow-x-auto gap-1">
                  {result.citations.map((c, i) => (
                    <button
                      key={i}
                      onClick={() => setActiveCitationTab(i)}
                      className={clsx(
                        "px-4 py-2 text-xs font-medium border-b-2 transition-all duration-150 whitespace-nowrap",
                        activeCitationTab === i
                          ? "border-brand text-brand bg-brand/5 font-semibold"
                          : "border-transparent text-ink-soft hover:text-ink hover:bg-parchment-warm/50"
                      )}
                    >
                      Source {i + 1} (Page {c.page_number})
                    </button>
                  ))}
                </div>

                {/* Selected Citation Content */}
                {result.citations[activeCitationTab] && (
                  <div className="citation-block mt-2 transition-opacity duration-200">
                    <div className="flex items-start justify-between mb-2 flex-wrap gap-2">
                      <div>
                        <p className="text-xs font-semibold text-brand">
                          {result.citations[activeCitationTab].document_title}
                        </p>
                        {result.citations[activeCitationTab].section_title && (
                          <p className="text-[10px] text-ink-muted mt-0.5">
                            {result.citations[activeCitationTab].section_title}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="text-[10px] text-ink-muted bg-white/80 px-2 py-0.5 rounded border border-parchment-border">
                          Page {result.citations[activeCitationTab].page_number}
                        </span>
                        <span
                          className={clsx(
                            "text-[10px] font-semibold bg-white/80 px-2 py-0.5 rounded border border-parchment-border",
                            confidenceColor(result.citations[activeCitationTab].confidence_score)
                          )}
                        >
                          Confidence: {Math.round(result.citations[activeCitationTab].confidence_score * 100)}%
                        </span>
                      </div>
                    </div>
                    <p className="evidence-text">{result.citations[activeCitationTab].evidence_text}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!result && !loading && (
          <div className="text-center py-16 text-ink-muted">
            <Scale className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p className="text-sm">Ask a question about your legal documents</p>
            <p className="text-xs mt-1">Every answer comes with exact page citations</p>
          </div>
        )}
      </div>
    </div>
  );
}
