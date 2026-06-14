import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export function useApplications(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["applications", params],
    queryFn: () => api.get("/applications/", { params }).then((r) => r.data),
  });
}

export function useApplication(id: string) {
  return useQuery({
    queryKey: ["application", id],
    queryFn: () => api.get(`/applications/${id}/`).then((r) => r.data),
    enabled: !!id,
  });
}

export function useApproveApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/applications/${id}/approve/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });
}

export function useSubmitApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/applications/${id}/submit/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });
}

export function useApprovalQueue() {
  return useQuery({
    queryKey: ["approval-queue"],
    queryFn: () => api.get("/applications/approval-queue/").then((r) => r.data),
    refetchInterval: 30000,
  });
}
