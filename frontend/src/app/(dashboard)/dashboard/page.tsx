"use client";

import { useDashboard } from "@/hooks/use-analytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Briefcase, FileText, Calendar, DollarSign, TrendingUp, Target } from "lucide-react";

export default function DashboardPage() {
  const { data, isLoading } = useDashboard();

  const stats = [
    { label: "Total Applications", value: data?.total_applications ?? 0, icon: FileText, color: "text-blue-600" },
    { label: "Submitted", value: data?.submitted ?? 0, icon: Briefcase, color: "text-green-600" },
    { label: "Interviews", value: data?.interviews ?? 0, icon: Calendar, color: "text-purple-600" },
    { label: "Offers", value: data?.offers ?? 0, icon: DollarSign, color: "text-yellow-600" },
    { label: "Response Rate", value: data ? `${data.response_rate}%` : "0%", icon: TrendingUp, color: "text-indigo-600" },
    { label: "Interview Rate", value: data ? `${data.interview_rate}%` : "0%", icon: Target, color: "text-pink-600" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Your job application overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                    {isLoading ? (
                      <Skeleton className="h-8 w-20 mt-1" />
                    ) : (
                      <p className="text-3xl font-bold mt-1">{stat.value}</p>
                    )}
                  </div>
                  <Icon className={`h-8 w-8 ${stat.color} opacity-80`} />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {data?.weekly_trend && data.weekly_trend.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Weekly Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {data.weekly_trend.map((week: any) => (
                <div key={week.week} className="flex items-center justify-between py-1">
                  <span className="text-sm">{new Date(week.week).toLocaleDateString()}</span>
                  <span className="text-sm font-medium">{week.count} applications</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
