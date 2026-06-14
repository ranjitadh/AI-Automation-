import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export function useCampaigns(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["campaigns", params],
    queryFn: () => api.get("/campaigns/", { params }).then((r) => r.data),
  });
}

export function useCampaign(id: string) {
  return useQuery({
    queryKey: ["campaign", id],
    queryFn: () => api.get(`/campaigns/${id}/`).then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => api.post("/campaigns/", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}

export function useStartCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/campaigns/${id}/start/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}
