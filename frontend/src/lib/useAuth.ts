"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { authApi } from "@/lib/api";

/**
 * Use this in every protected page.
 * Returns { ready: boolean } — render nothing until ready=true.
 *
 * Usage:
 *   const { ready } = useAuth();
 *   if (!ready) return null;
 */
export function useAuth() {
  const router = useRouter();
  const { token, user, setAuth, logout } = useAuthStore();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!token) {
      router.replace("/login");
      return;
    }
    // If user already hydrated from a previous call this session, skip fetch
    if (user) {
      setReady(true);
      return;
    }
    // Validate token by fetching /me
    authApi
      .me()
      .then((res) => {
        setAuth(res.data, token);
        setReady(true);
      })
      .catch(() => {
        logout();
        router.replace("/login");
      });
  }, [token]);

  return { ready };
}
