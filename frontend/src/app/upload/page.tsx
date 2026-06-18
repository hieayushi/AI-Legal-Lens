"use client";
import { useState, useCallback } from "react";
import { docsApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { Upload, FileText, CheckCircle, XCircle, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import Link from "next/link";

const DOC_TYPES = [
  { value: "judgment", label: "Court Judgment" },
  { value: "policy", label: "Government Policy" },
  { value: "circular", label: "Circular / Notification" },
  { value: "regulation", label: "Regulation" },
  { value: "order", label: "Administrative Order" },
  { value: "compliance", label: "Compliance Manual" },
  { value: "tender", label: "Tender Document" },
  { value: "other", label: "Other" },
];

type UploadState = "idle" | "uploading" | "success" | "error";

export default function UploadPage() {
  const { ready } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [docType, setDocType] = useState("judgment");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [state, setState] = useState<UploadState>("idle");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f?.type === "application/pdf") setFile(f);
    else toast.error("Only PDF files are supported");
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setState("uploading");
    setError("");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("doc_type", docType);
    if (title) fd.append("title", title);
    if (description) fd.append("description", description);
    if (tags) fd.append("tags", tags);
    try {
      const r = await docsApi.upload(fd);
      setResult(r.data);
      setState("success");
      toast.success("Document indexed successfully");
    } catch (e: any) {
      setState("error");
      setError(e.response?.data?.detail || "Upload failed");
      toast.error("Upload failed");
    }
  };

  const reset = () => {
    setFile(null);
    setTitle("");
    setDescription("");
    setTags("");
    setState("idle");
    setResult(null);
    setError("");
  };

  if (!ready) return null;

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-ink">Upload Document</h1>
        <p className="text-sm text-ink-muted mt-0.5">
          PDFs are processed, TOC extracted, and pages indexed hierarchically
        </p>
      </div>

      {state === "success" && result ? (
        <div className="card text-center py-10">
          <CheckCircle className="w-12 h-12 text-verdict-green mx-auto mb-3" />
          <h2 className="font-display font-semibold text-ink text-lg mb-1">{result.title}</h2>
          <p className="text-sm text-ink-muted mb-4">
            {result.page_count} pages indexed ·{" "}
            {result.is_scanned ? "OCR applied" : "Native text extracted"}
          </p>
          <div className="flex justify-center gap-3">
            <button onClick={reset} className="btn-secondary">
              Upload Another
            </button>
            <Link href="/query" className="btn-primary">
              Ask a Question
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            className={clsx(
              "border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer",
              dragOver
                ? "border-brand bg-brand-light"
                : file
                ? "border-brand bg-brand-light"
                : "border-parchment-border hover:border-brand/50"
            )}
            onClick={() => document.getElementById("file-input")?.click()}
          >
            <input
              id="file-input"
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={handleFileSelect}
            />
            {file ? (
              <>
                <FileText className="w-10 h-10 text-brand mx-auto mb-2" />
                <p className="font-medium text-sm text-ink">{file.name}</p>
                <p className="text-xs text-ink-muted mt-1">
                  {(file.size / 1024 / 1024).toFixed(1)} MB
                </p>
              </>
            ) : (
              <>
                <Upload className="w-10 h-10 text-ink-muted mx-auto mb-2" />
                <p className="text-sm text-ink">Drop a PDF here or click to browse</p>
                <p className="text-xs text-ink-muted mt-1">Maximum 50MB</p>
              </>
            )}
          </div>

          {/* Metadata */}
          <div className="card space-y-4">
            <div>
              <label className="text-xs font-medium text-ink-soft block mb-1">
                Document Type
              </label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="input"
              >
                {DOC_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-ink-soft block mb-1">
                Title{" "}
                <span className="text-ink-muted font-normal">
                  (auto-detected if empty)
                </span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. State of Maharashtra v. Accused Person"
                className="input"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-ink-soft block mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of this document..."
                rows={2}
                className="input resize-none"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-ink-soft block mb-1">
                Tags{" "}
                <span className="text-ink-muted font-normal">(comma-separated)</span>
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="bail, section-420, fraud, high-court"
                className="input"
              />
            </div>
          </div>

          {/* Error */}
          {state === "error" && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg p-3">
              <XCircle className="w-4 h-4 text-verdict-red flex-shrink-0" />
              <p className="text-xs text-verdict-red">{error}</p>
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleUpload}
            disabled={!file || state === "uploading"}
            className="btn-primary w-full py-2.5 flex items-center justify-center gap-2"
          >
            {state === "uploading" ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing & Indexing...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Upload & Index
              </>
            )}
          </button>

          {state === "uploading" && (
            <p className="text-center text-xs text-ink-muted">
              Extracting text, detecting structure, building page index...
            </p>
          )}
        </div>
      )}
    </div>
  );
}
