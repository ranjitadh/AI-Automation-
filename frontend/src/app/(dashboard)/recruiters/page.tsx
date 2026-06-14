"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Plus, Linkedin, Mail, MessageSquare } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function RecruitersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["recruiters"],
    queryFn: () => api.get("/recruiters/").then((r) => r.data),
  });

  const recruiters = data?.results || data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Recruiters</h1>
          <p className="text-muted-foreground">Track and manage recruiter relationships</p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4 mr-2" />Add Recruiter</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Recruiter</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <Input placeholder="Full Name" />
              <Input placeholder="Company" />
              <Input placeholder="Title" />
              <Input placeholder="Email" type="email" />
              <Input placeholder="LinkedIn URL" />
              <Button>Save Recruiter</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map((i) => <Skeleton key={i} className="h-32" />)}
        </div>
      ) : Array.isArray(recruiters) && recruiters.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {recruiters.map((r: any) => (
            <Card key={r.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{r.name}</CardTitle>
                    <p className="text-sm text-muted-foreground">{r.title} at {r.company_name}</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  {r.email && (
                    <p className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      {r.email}
                    </p>
                  )}
                  {r.linkedin_url && (
                    <p className="flex items-center gap-2">
                      <Linkedin className="h-4 w-4 text-muted-foreground" />
                      <a href={r.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline truncate">
                        LinkedIn Profile
                      </a>
                    </p>
                  )}
                </div>
                <div className="flex gap-2 mt-4">
                  <Button size="sm" variant="outline">
                    <MessageSquare className="h-4 w-4 mr-1" />Message
                  </Button>
                  <Button size="sm" variant="ghost">
                    <Mail className="h-4 w-4 mr-1" />Email
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">No recruiters added yet</CardContent>
        </Card>
      )}
    </div>
  );
}
