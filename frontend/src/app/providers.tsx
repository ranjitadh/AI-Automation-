"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/store/auth-store";
import { useRouter, usePathname } from "next/navigation";

const publicRoutes = ["/login", "/register", "/forgot-password"];

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, loadUser } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    loadUser().finally(() => setInitialized(true));
  }, []);

  useEffect(() => {
    if (!initialized) return;
    if (!isAuthenticated && !publicRoutes.includes(pathname)) {
      router.push("/login");
    }
    if (isAuthenticated && publicRoutes.includes(pathname)) {
      router.push("/dashboard");
    }
  }, [initialized, isAuthenticated, pathname, router]);

  if (!initialized || (!isAuthenticated && !publicRoutes.includes(pathname))) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthGuard>{children}</AuthGuard>
    </QueryClientProvider>
  );
}
