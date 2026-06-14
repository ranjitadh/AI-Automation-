"use client";

import { useDashboard, useAnalyticsFunnel } from "@/hooks/use-analytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { BarChart3, TrendingUp, Users, Send, Eye, CheckCircle, Calendar, DollarSign } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export default function AnalyticsPage() {
  const { data: dashboard, isLoading } = useDashboard();
  const { data: funnel } = useAnalyticsFunnel();

  const { data: trends } = useQuery({
    queryKey: ["analytics-trends"],
    queryFn: () => api.get("/analytics/trends/").then((r) => r.data),
  });

  const stages = funnel?.stages || {};
  const total = funnel?.total || 1;

  const stageConfig = [
    { key: "discovered", label: "Discovered", icon: Eye, color: "bg-blue-500" },
    { key: "analyzed", label: "Analyzed", icon: BarChart3, color: "bg-indigo-500" },
    { key: "approved", label: "Approved", icon: CheckCircle, color: "bg-purple-500" },
    { key: "submitted", label: "Submitted", icon: Send, color: "bg-green-500" },
    { key: "interview", label: "Interview", icon: Calendar, color: "bg-yellow-500" },
    { key: "offer", label: "Offer", icon: DollarSign, color: "bg-emerald-500" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">Track your application performance</p>
      </div>

      {isLoading ? (
        <div className="space-y-4">{[1,2,3].map((i) => <Skeleton key={i} className="h-32" />)}</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Response Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{dashboard?.response_rate || 0}%</p>
                <Progress value={dashboard?.response_rate || 0} className="mt-2" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Interview Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{dashboard?.interview_rate || 0}%</p>
                <Progress value={dashboard?.interview_rate || 0} className="mt-2" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Last 30 Days</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{dashboard?.last_30_days || 0}</p>
                <p className="text-sm text-muted-foreground mt-1">applications</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Application Funnel</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {stageConfig.map((stage) => {
                  const count = stages[stage.key] || 0;
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                  return (
                    <div key={stage.key} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <stage.icon className="h-4 w-4 text-muted-foreground" />
                          <span>{stage.label}</span>
                        </div>
                        <span className="font-medium">{count} ({pct}%)</span>
                      </div>
                      <div className="w-full bg-secondary rounded-full h-2">
                        <div className={`h-2 rounded-full ${stage.color}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {Array.isArray(trends) && trends.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {trends.map((t: any) => (
                    <div key={t.period} className="flex items-center justify-between py-1 border-b last:border-0">
                      <span className="text-sm">{t.period}</span>
                      <div className="flex gap-4 text-sm">
                        <span>Total: {t.total}</span>
                        <span className="text-green-600">Submitted: {t.submitted}</span>
                        <span className="text-purple-600">Interviews: {t.interviews}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
