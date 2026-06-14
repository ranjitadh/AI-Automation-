"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, formatCurrency } from "@/lib/utils";

const statusColors: Record<string, "default" | "success" | "warning" | "destructive" | "secondary"> = {
  negotiating: "warning",
  accepted: "success",
  declined: "destructive",
  expired: "secondary",
  withdrawn: "secondary",
};

export default function OffersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["offers"],
    queryFn: () => api.get("/offers/").then((r) => r.data),
  });

  const offers = data?.results || data || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Offers</h1>
        <p className="text-muted-foreground">Track and compare job offers</p>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[1,2,3].map((i) => <Skeleton key={i} className="h-32" />)}</div>
      ) : Array.isArray(offers) && offers.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {offers.map((offer: any) => (
            <Card key={offer.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{offer.job_title}</CardTitle>
                    <p className="text-sm text-muted-foreground">{offer.company_name}</p>
                  </div>
                  <Badge variant={statusColors[offer.status] || "secondary"}>{offer.status}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Base Salary</p>
                    <p className="font-semibold">{formatCurrency(offer.base_salary)}</p>
                  </div>
                  {offer.equity && (
                    <div>
                      <p className="text-sm text-muted-foreground">Equity</p>
                      <p className="font-semibold">{offer.equity}</p>
                    </div>
                  )}
                  {offer.signing_bonus && (
                    <div>
                      <p className="text-sm text-muted-foreground">Signing Bonus</p>
                      <p className="font-semibold">{formatCurrency(offer.signing_bonus)}</p>
                    </div>
                  )}
                  {offer.start_date && (
                    <div>
                      <p className="text-sm text-muted-foreground">Start Date</p>
                      <p className="font-semibold">{formatDate(offer.start_date)}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">No offers yet</CardContent>
        </Card>
      )}
    </div>
  );
}
