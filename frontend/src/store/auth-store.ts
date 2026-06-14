import { create } from "zustand";
import api from "@/lib/api";

interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string;
  timezone: string;
  locale: string;
  date_joined: string;
}

interface Organization {
  id: string;
  name: string;
  slug: string;
  role: string;
  member_count: number;
}

interface AuthState {
  user: User | null;
  organizations: Organization[];
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string, organization_name: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  switchOrg: (orgId: string) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  organizations: [],
  isAuthenticated: false,
  isLoading: true,

  login: async (email, password) => {
    const res = await api.post("/auth/login/", { email, password });
    localStorage.setItem("access_token", res.data.access);
    localStorage.setItem("refresh_token", res.data.refresh);
    set({
      user: res.data.user,
      organizations: res.data.organizations || [],
      isAuthenticated: true,
      isLoading: false,
    });
    if (res.data.organizations?.length > 0) {
      localStorage.setItem("organization_id", res.data.organizations[0].id);
    }
  },

  register: async (email, password, full_name, organization_name) => {
    const res = await api.post("/auth/register/", {
      email, password, full_name, organization_name,
    });
    localStorage.setItem("access_token", res.data.access);
    localStorage.setItem("refresh_token", res.data.refresh);
    localStorage.setItem("organization_id", res.data.organization.id);
    set({
      user: res.data.user,
      organizations: [res.data.organization],
      isAuthenticated: true,
      isLoading: false,
    });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("organization_id");
    set({ user: null, organizations: [], isAuthenticated: false, isLoading: false });
  },

  loadUser: async () => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        set({ isLoading: false });
        return;
      }
      const res = await api.get("/auth/me/");
      set({
        user: res.data,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      set({ isLoading: false });
    }
  },

  switchOrg: async (orgId) => {
    try {
      await api.post(`/orgs/${orgId}/switch/`);
      localStorage.setItem("organization_id", orgId);
    } catch (e) {
      console.error("Failed to switch org", e);
    }
  },
}));
