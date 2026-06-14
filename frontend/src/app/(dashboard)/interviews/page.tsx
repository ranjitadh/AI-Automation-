"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/utils";
import { Calendar, Clock, Video, Phone } from "lucide-react";

const typeIcons: Record<string, any> = {
  phone: Phone,
  video: Video,
  onsite: Calendar,
  technical: Clock,
};

export default function InterviewsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["interviews"],
    queryFn: () => api.get("/interviews/").then((r) => r.data),
  });

  const interviews = data?.results || data || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Interviews</h1>
        <p className="text-muted-foreground">Track your interview pipeline</p>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[1,2,3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      ) : Array.isArray(interviews) && interviews.length > 0 ? (
        <div className="space-y-4">
          {interviews.map((iv: any) => {
            const Icon = typeIcons[iv.interview_type] || Calendar;
            return (
              <Card key={iv.id}>
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <div className="p-2 rounded-md bg-primary/10">
                      <Icon className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-semibold">{iv.job_title}</h3>
                          <p className="text-sm text-muted-foreground">{iv.company_name}</p>
                        </div>
                        <Badge variant={iv.status === "scheduled" ? "warning" : iv.status === "completed" ? "success" : "secondary"}>
                          {iv.status}
                        </Badge>
                      </div>
                      <div className="flex gap-4 mt-2 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          {formatDate(iv.scheduled_at)}
                        </span>
                        <span>Round {iv.round}</span>
                        <span className="capitalize">{iv.interview_type}</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">No interviews scheduled</CardContent>
        </Card>
      )}
    </div>
  );
}
