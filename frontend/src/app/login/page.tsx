"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi, BASE_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Scale, Loader2, Eye, EyeOff } from "lucide-react";
import toast from "react-hot-toast";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);

const handleSubmit = async () => {
  console.debug("[LOGIN PAGE] SUBMIT", { mode, email, fullName, BASE_URL });
  if (!email || !password) return;
  if (mode === "register" && !fullName) {
    toast.error("Full name is required");
    return;
  }
  setLoading(true);
  try {
    const res =
      mode === "login"
        ? await authApi.login(email, password)
        : await authApi.register(email, password, fullName);

    const { access_token, user } = res.data;

    // Use the backend user object directly
    setAuth(user, access_token);
    toast.success(mode === "login" ? "Welcome back!" : "Account created!");
    router.push("/dashboard");
  } catch (e: any) {
    toast.error(e.response?.data?.detail || "Authentication failed");
  } finally {
    setLoading(false);
  }
};

  return (
    <div className="min-h-screen bg-parchment flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-brand rounded-xl mb-3">
            <Scale className="w-6 h-6 text-white" />
          </div>
          <h1 className="font-display text-2xl font-bold text-ink">LegalLens AI</h1>
          <p className="text-sm text-ink-muted mt-1">Judicial Intelligence Platform</p>
        </div>

        {/* Card */}
        <div className="card">
          {/* Mode toggle */}
          <div className="flex bg-parchment-warm rounded-lg p-1 mb-5">
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  mode === m
                    ? "bg-white text-ink shadow-card"
                    : "text-ink-muted hover:text-ink"
                }`}
              >
                {m === "login" ? "Sign In" : "Register"}
              </button>
            ))}
          </div>

          <div className="space-y-3">
            {mode === "register" && (
              <div>
                <label className="text-xs font-medium text-ink-soft block mb-1">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Ayushi Sharma"
                  className="input"
                />
              </div>
            )}

            <div>
              <label className="text-xs font-medium text-ink-soft block mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="input"
                onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              />
            </div>

            <div>
              <label className="text-xs font-medium text-ink-soft block mb-1">Password</label>
              <div className="relative">
                <input
                  type={showPass ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  className="input pr-10"
                  onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink"
                >
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn-primary w-full py-2.5 flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {mode === "login" ? "Signing in..." : "Creating account..."}
                </>
              ) : mode === "login" ? (
                "Sign In"
              ) : (
                "Create Account"
              )}
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-ink-muted mt-4">
          {mode === "login" ? "No account? " : "Already registered? "}
          <button
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            className="text-brand hover:underline"
          >
            {mode === "login" ? "Register here" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
