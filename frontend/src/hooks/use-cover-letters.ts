import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export function useCoverLetters() {
  return useQuery({
    queryKey: ["cover-letters"],
    queryFn: () => api.get("/cover-letters/").then((r) => r.data),
  });
}

export function useGenerateCoverLetter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { job: string; resume?: string; style?: string }) =>
      api.post("/cover-letters/generate/", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cover-letters"] }),
  });
}
