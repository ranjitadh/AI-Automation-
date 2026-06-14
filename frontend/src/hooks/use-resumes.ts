import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export function useResumes() {
  return useQuery({
    queryKey: ["resumes"],
    queryFn: () => api.get("/resumes/").then((r) => r.data),
  });
}

export function useResume(id: string) {
  return useQuery({
    queryKey: ["resume", id],
    queryFn: () => api.get(`/resumes/${id}/`).then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreateResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => api.post("/resumes/", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["resumes"] }),
  });
}

export function useSetActiveResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/resumes/${id}/set-active/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["resumes"] }),
  });
}
