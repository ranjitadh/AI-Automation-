"use client";

import { useState } from "react";
import { useApplications, useApproveApplication, useSubmitApplication, useApprovalQueue } from "@/hooks/use-applications";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatDate, getScoreBg } from "@/lib/utils";
import { Check, X, Send, Loader2 } from "lucide-react";

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  discovered: "secondary",
  analyzed: "warning",
  approved: "default",
  submitted: "success",
  interview: "success",
  offer: "success",
  rejected: "destructive",
  failed: "destructive",
};

export default function ApplicationsPage() {
  const [tab, setTab] = useState("all");
  const { data: allApps, isLoading } = useApplications(tab === "queue" ? { status: "analyzed" } : {});
  const { data: queue } = useApprovalQueue();
  const approve = useApproveApplication();
  const submit = useSubmitApplication();
  const [selected, setSelected] = useState<any>(null);

  const apps = tab === "queue" ? queue?.results || queue || [] : allApps?.results || allApps || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Applications</h1>
        <p className="text-muted-foreground">Track and manage job applications</p>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="all">All Applications</TabsTrigger>
          <TabsTrigger value="queue">Approval Queue</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          {isLoading ? (
            <div className="space-y-2">{[1,2,3,4].map((i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
          ) : (
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Job</TableHead>
                      <TableHead>Company</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Cover Letter</TableHead>
                      <TableHead>Submitted</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Array.isArray(apps) && apps.length > 0 ? apps.map((app: any) => (
                      <TableRow key={app.id} className="cursor-pointer" onClick={() => setSelected(app)}>
                        <TableCell className="font-medium">{app.job_title}</TableCell>
                        <TableCell>{app.company_name}</TableCell>
                        <TableCell>
                          <Badge variant={statusColors[app.status] || "secondary"}>{app.status}</Badge>
                        </TableCell>
                        <TableCell className="max-w-xs truncate">{app.cover_letter?.content?.slice(0, 100) || "N/A"}</TableCell>
                        <TableCell>{formatDate(app.submitted_at)}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            {app.status === "analyzed" && (
                              <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); approve.mutate(app.id); }}>
                                <Check className="h-4 w-4 mr-1" />Approve
                              </Button>
                            )}
                            {app.status === "approved" && (
                              <Button size="sm" onClick={(e) => { e.stopPropagation(); submit.mutate(app.id); }} disabled={submit.isPending}>
                                {submit.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Send className="h-4 w-4 mr-1" />}
                                Submit
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                          No applications yet
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="queue">
          {Array.isArray(queue?.results || queue) && (queue?.results || queue).length > 0 ? (
            <div className="space-y-4">
              {(queue?.results || queue).map((app: any) => (
                <Card key={app.id}>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold">{app.job_title}</h3>
                        <p className="text-sm text-muted-foreground">{app.company_name}</p>
                        {app.cover_letter?.content && (
                          <div className="mt-2 p-3 bg-muted rounded-md text-sm max-h-32 overflow-y-auto">
                            {app.cover_letter.content}
                          </div>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => { approve.mutate(app.id); }}>
                          <Check className="h-4 w-4 mr-1" />Approve
                        </Button>
                        <Button size="sm" variant="destructive">
                          <X className="h-4 w-4 mr-1" />Reject
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-12 text-muted-foreground">
                No applications awaiting approval
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
