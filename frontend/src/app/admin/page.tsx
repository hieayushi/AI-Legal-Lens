"use client";
import { useEffect, useState } from "react";
import { docsApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { Shield, Trash2, RefreshCw, FileText, AlertTriangle } from "lucide-react";
import toast from "react-hot-toast";

export default function AdminPage() {
  const { ready } = useAuth();
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchDocs = () => {
    setLoading(true);
    docsApi.list()
      .then((r) => setDocuments(r.data))
      .catch(() => toast.error("Failed to load documents"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { if (ready) fetchDocs(); }, [ready]);

  if (!ready) return null;

  const handleDelete = async (id: string, title: string) => {
    if (!confirm(`Delete "${title}"? This removes the document and all indexed pages.`)) return;
    setDeleting(id);
    try {
      await docsApi.delete(id);
      toast.success("Document deleted");
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch {
      toast.error("Delete failed");
    } finally {
      setDeleting(null);
    }
  };

  const statusColor: Record<string, string> = {
    indexed: "text-verdict-green", processing: "text-verdict-amber",
    failed: "text-verdict-red", pending: "text-ink-muted",
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-brand" />
          <h1 className="text-2xl font-display font-semibold text-ink">Admin Panel</h1>
        </div>
        <button onClick={fetchDocs} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="card mb-5 flex items-start gap-3 bg-amber-50 border-amber-200">
        <AlertTriangle className="w-4 h-4 text-verdict-amber flex-shrink-0 mt-0.5" />
        <p className="text-xs text-verdict-amber">
          Deleting a document removes it and all indexed pages permanently. Query logs referencing it are retained.
        </p>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => <div key={i} className="card skeleton h-16" />)}
        </div>
      ) : documents.length === 0 ? (
        <div className="card text-center py-16">
          <FileText className="w-10 h-10 text-ink-muted mx-auto mb-2 opacity-30" />
          <p className="text-sm text-ink-muted">No documents in the system.</p>
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-parchment-warm">
              <tr className="text-left text-xs text-ink-muted">
                <th className="px-4 py-3 font-medium">Document</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Pages</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Uploaded</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-t border-parchment-border hover:bg-parchment/50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-ink truncate max-w-[240px]">{doc.title}</div>
                    {doc.case_number && (
                      <div className="text-xs text-ink-muted font-mono">{doc.case_number}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-ink-soft capitalize">{doc.doc_type}</td>
                  <td className="px-4 py-3 text-ink-soft">{doc.page_count}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium capitalize ${statusColor[doc.processing_status] || "text-ink-muted"}`}>
                      {doc.processing_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-ink-muted text-xs">
                    {doc.created_at ? new Date(doc.created_at).toLocaleDateString("en-IN") : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDelete(doc.id, doc.title)}
                      disabled={deleting === doc.id}
                      className="text-ink-muted hover:text-verdict-red transition-colors disabled:opacity-40"
                      title="Delete document"
                    >
                      {deleting === doc.id
                        ? <RefreshCw className="w-4 h-4 animate-spin" />
                        : <Trash2 className="w-4 h-4" />}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
