"use client";

import { useState } from "react";
import { useCampaigns, useCreateCampaign, useStartCampaign } from "@/hooks/use-campaigns";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { formatDate } from "@/lib/utils";
import { Plus, Play, Pause, Loader2 } from "lucide-react";

export default function CampaignsPage() {
  const { data, isLoading } = useCampaigns();
  const createCampaign = useCreateCampaign();
  const startCampaign = useStartCampaign();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", target_titles: "", target_locations: "", auto_apply: false });

  const handleCreate = async () => {
    await createCampaign.mutateAsync({
      name: form.name,
      description: form.description,
      target_titles: form.target_titles ? form.target_titles.split(",").map((s) => s.trim()) : [],
      target_locations: form.target_locations ? form.target_locations.split(",").map((s) => s.trim()) : [],
      auto_apply: form.auto_apply,
    });
    setOpen(false);
    setForm({ name: "", description: "", target_titles: "", target_locations: "", auto_apply: false });
  };

  const campaigns = data?.results || data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Campaigns</h1>
          <p className="text-muted-foreground">Create and manage job discovery campaigns</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4 mr-2" />New Campaign</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Campaign</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <Input placeholder="Campaign Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <Input placeholder="Target Titles (comma-separated)" value={form.target_titles} onChange={(e) => setForm({ ...form, target_titles: e.target.value })} />
              <Input placeholder="Target Locations (comma-separated)" value={form.target_locations} onChange={(e) => setForm({ ...form, target_locations: e.target.value })} />
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.auto_apply} onChange={(e) => setForm({ ...form, auto_apply: e.target.checked })} />
                Auto-apply jobs
              </label>
              <Button onClick={handleCreate} disabled={createCampaign.isPending}>Create Campaign</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map((i) => <Skeleton key={i} className="h-40" />)}
        </div>
      ) : Array.isArray(campaigns) && campaigns.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {campaigns.map((c: any) => (
            <Card key={c.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{c.name}</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">{c.description || "No description"}</p>
                  </div>
                  <Badge variant={c.status === "active" ? "success" : c.status === "paused" ? "warning" : "secondary"}>
                    {c.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Jobs Found</span>
                    <span className="font-medium">{c.jobs_found}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Submitted</span>
                    <span className="font-medium">{c.applications_submitted}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Run</span>
                    <span>{formatDate(c.last_run_at)}</span>
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  {c.status !== "active" && (
                    <Button size="sm" onClick={() => startCampaign.mutate(c.id)} disabled={startCampaign.isPending}>
                      {startCampaign.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Play className="h-4 w-4 mr-1" />}
                      Start
                    </Button>
                  )}
                  {c.status === "active" && (
                    <Button size="sm" variant="outline"><Pause className="h-4 w-4 mr-1" />Pause</Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">
            No campaigns yet. Create your first campaign to start discovering jobs.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
