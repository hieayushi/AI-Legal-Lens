import { create } from "zustand";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthStore {
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  isAdmin: () => boolean;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  token: typeof window !== "undefined" ? localStorage.getItem("ll_token") : null,
  setAuth: (user, token) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("ll_token", token);
    }
    set({ user, token });
  },
  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("ll_token");
    }
    set({ user: null, token: null });
  },
  isAdmin: () => get().user?.role === "admin",
}));
