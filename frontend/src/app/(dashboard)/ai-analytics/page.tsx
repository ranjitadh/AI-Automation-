"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart3, DollarSign, Cpu, Activity, AlertTriangle } from "lucide-react";
import api from "@/lib/api";

type Analytics = {
  totals: {
    total_requests: number;
    total_cost: string;
    total_tokens: number;
    avg_latency: number;
  };
  budget: {
    allowed: boolean;
    daily: { spend_cents: number; limit_cents: number };
    weekly: { spend_cents: number; limit_cents: number };
    monthly: { spend_cents: number; limit_cents: number };
    reason?: string;
  };
  by_task: Array<{ task_type: string; count: number; total_cost: string; avg_latency: number }>;
  by_provider: Array<{ provider: string; model: string; count: number; total_cost: string; avg_latency: number }>;
};

export default function AIAnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/api/v1/ai/analytics/?days=30").then((r) => {
      setData(r.data as Analytics);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">AI Analytics</h1>
        <p className="text-muted-foreground">No AI usage data yet. Start using the Career Agent to see analytics.</p>
      </div>
    );
  }

  const spendDollars = (cents: number) => `$${(cents / 100).toFixed(2)}`;
  const pct = (spent: number, limit: number) => limit > 0 ? Math.round((spent / limit) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <BarChart3 className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">AI Analytics</h1>
          <p className="text-muted-foreground">Usage, costs, and performance metrics</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Cpu className="h-4 w-4" /> Total Requests
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{data.totals.total_requests.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <DollarSign className="h-4 w-4" /> Total Cost
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">${parseFloat(data.totals.total_cost || "0").toFixed(4)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4" /> Avg Latency
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{Math.round(data.totals.avg_latency || 0)}ms</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <DollarSign className="h-4 w-4" /> Total Tokens
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{(data.totals.total_tokens || 0).toLocaleString()}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" /> Budget Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm font-medium">Daily</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-secondary h-2 rounded-full">
                  <div className={`h-2 rounded-full ${pct(data.budget.daily.spend_cents, data.budget.daily.limit_cents) > 80 ? "bg-red-500" : "bg-primary"}`}
                    style={{ width: `${Math.min(pct(data.budget.daily.spend_cents, data.budget.daily.limit_cents), 100)}%` }} />
                </div>
                <span className="text-xs">{spendDollars(data.budget.daily.spend_cents)} / {spendDollars(data.budget.daily.limit_cents)}</span>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium">Weekly</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-secondary h-2 rounded-full">
                  <div className={`h-2 rounded-full ${pct(data.budget.weekly.spend_cents, data.budget.weekly.limit_cents) > 80 ? "bg-red-500" : "bg-primary"}`}
                    style={{ width: `${Math.min(pct(data.budget.weekly.spend_cents, data.budget.weekly.limit_cents), 100)}%` }} />
                </div>
                <span className="text-xs">{spendDollars(data.budget.weekly.spend_cents)} / {spendDollars(data.budget.weekly.limit_cents)}</span>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium">Monthly</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-secondary h-2 rounded-full">
                  <div className={`h-2 rounded-full ${pct(data.budget.monthly.spend_cents, data.budget.monthly.limit_cents) > 80 ? "bg-red-500" : "bg-primary"}`}
                    style={{ width: `${Math.min(pct(data.budget.monthly.spend_cents, data.budget.monthly.limit_cents), 100)}%` }} />
                </div>
                <span className="text-xs">{spendDollars(data.budget.monthly.spend_cents)} / {spendDollars(data.budget.monthly.limit_cents)}</span>
              </div>
            </div>
          </div>
          {!data.budget.allowed && (
            <p className="text-sm text-red-500 mt-2">Budget limit reached ({data.budget.reason})</p>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Usage by Task Type</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {data.by_task.map((t) => (
                <div key={t.task_type} className="flex items-center justify-between text-sm">
                  <span className="capitalize">{t.task_type.replace(/_/g, " ")}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-muted-foreground">{t.count} req</span>
                    <span className="font-mono text-xs">${parseFloat(t.total_cost || "0").toFixed(4)}</span>
                    <Badge variant="outline" className="text-[10px]">{Math.round(t.avg_latency)}ms</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Usage by Provider</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {data.by_provider.map((p) => (
                <div key={`${p.provider}-${p.model}`} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{p.provider}</Badge>
                    <span className="font-mono text-xs">{p.model}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-muted-foreground">{p.count} req</span>
                    <span className="font-mono text-xs">${parseFloat(p.total_cost || "0").toFixed(4)}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
