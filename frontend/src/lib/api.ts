import axios from "axios";

export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://ai-legal-lens.onrender.com/api/v1";
console.debug("[API] BASE_URL", BASE_URL);

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2 min for LLM responses
});

// Attach JWT token on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    console.debug("[API REQUEST]", config.method, config.baseURL, config.url, config.data);
    const token = localStorage.getItem("ll_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle 401 globally
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (typeof window !== "undefined") {
      console.error("[API ERROR]", error?.response?.status, error?.response?.data, error?.message);
    }
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("ll_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ── Auth ─────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
  register: (email: string, password: string, full_name: string) =>
    api.post("/auth/register", { email, password, full_name }),
  me: () => api.get("/auth/me"),
};

// ── Documents ────────────────────────────────

export const docsApi = {
  upload: (formData: FormData) =>
    api.post("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  list: (docType?: string) =>
    api.get("/documents/", { params: docType ? { doc_type: docType } : {} }),
  get: (id: string) => api.get(`/documents/${id}`),
  delete: (id: string) => api.delete(`/documents/${id}`),
  getToc: (id: string) => api.get(`/documents/${id}/toc`),
  getPages: (id: string, pageNumber?: number) =>
    api.get(`/documents/${id}/pages`, { params: pageNumber ? { page_number: pageNumber } : {} }),
  getPdfUrl: (id: string) => `${BASE_URL}/documents/${id}/file`,
};

// ── Query ────────────────────────────────────

export const queryApi = {
  ask: (query: string, documentIds: string[], method = "hierarchical", topK = 5) =>
    api.post("/query/ask", {
      query,
      document_ids: documentIds,
      retrieval_method: method,
      top_k: topK,
    }),
  history: (limit = 20) => api.get("/query/history", { params: { limit } }),
  get: (id: string) => api.get(`/query/${id}`),
  feedback: (id: string, score: number) =>
    api.post(`/query/${id}/feedback`, null, { params: { score } }),
  summarize: (docId: string, type = "full") =>
    api.post(`/query/summarize/${docId}`, null, { params: { summary_type: type } }),
  compare: (documentIds: string[], query: string) =>
    api.post("/query/compare", documentIds, { params: { query } }),
};

// ── Analytics ────────────────────────────────

export const analyticsApi = {
  summary: (days = 30) => api.get("/analytics/summary", { params: { days } }),
  document: (id: string) => api.get(`/analytics/document/${id}`),
};

// ── Evaluation ───────────────────────────────

export const evalApi = {
  startRun: (method: string, datasetPath: string) =>
    api.post("/eval/run", { retrieval_method: method, dataset_path: datasetPath }),
  listRuns: () => api.get("/eval/runs"),
  getRun: (runId: string) => api.get(`/eval/runs/${runId}`),
  compare: () => api.get("/eval/compare"),
};
