import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export function useJobs(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["jobs", params],
    queryFn: () => api.get("/jobs/", { params }).then((r) => r.data),
  });
}

export function useJob(id: string) {
  return useQuery({
    queryKey: ["job", id],
    queryFn: () => api.get(`/jobs/${id}/`).then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => api.post("/jobs/", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useAnalyzeJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/jobs/${id}/analyze/`),
    onSuccess: (_: any, id: string) => qc.invalidateQueries({ queryKey: ["job", id] }),
  });
}
