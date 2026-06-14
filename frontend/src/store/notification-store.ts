import { create } from "zustand";
import api from "@/lib/api";

interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  loadNotifications: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,

  loadNotifications: async () => {
    try {
      const [notifRes, countRes] = await Promise.all([
        api.get("/notifications/?page_size=20"),
        api.get("/notifications/unread-count/"),
      ]);
      set({
        notifications: notifRes.data.results || notifRes.data,
        unreadCount: countRes.data.count || 0,
      });
    } catch {
      // silently fail
    }
  },

  markRead: async (id) => {
    try {
      await api.patch(`/notifications/${id}/read/`);
      const notifications = get().notifications.map((n) =>
        n.id === id ? { ...n, is_read: true } : n
      );
      set({
        notifications,
        unreadCount: Math.max(0, get().unreadCount - 1),
      });
    } catch {}
  },

  markAllRead: async () => {
    try {
      await api.post("/notifications/read-all/");
      set({
        notifications: get().notifications.map((n) => ({ ...n, is_read: true })),
        unreadCount: 0,
      });
    } catch {}
  },
}));
