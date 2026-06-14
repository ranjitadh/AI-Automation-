import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get("/analytics/dashboard/").then((r) => r.data),
    refetchInterval: 60000,
  });
}

export function useAnalyticsFunnel() {
  return useQuery({
    queryKey: ["analytics-funnel"],
    queryFn: () => api.get("/analytics/funnel/").then((r) => r.data),
  });
}

export function useAnalyticsTrends(period = "month") {
  return useQuery({
    queryKey: ["analytics-trends", period],
    queryFn: () => api.get("/analytics/trends/", { params: { period } }).then((r) => r.data),
  });
}
