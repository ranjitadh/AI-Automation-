"use client";

import { useResumes, useCreateResume, useSetActiveResume } from "@/hooks/use-resumes";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useState } from "react";
import { Plus, Star, Upload, Loader2 } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function ResumesPage() {
  const { data, isLoading } = useResumes();
  const createResume = useCreateResume();
  const setActive = useSetActiveResume();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");

  const handleCreate = async () => {
    await createResume.mutateAsync({ title, profile_slug: title.toLowerCase().replace(/\s+/g, "-") });
    setOpen(false);
    setTitle("");
  };

  const resumes = data?.results || data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Resumes</h1>
          <p className="text-muted-foreground">Manage your resume profiles</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4 mr-2" />New Resume</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Resume Profile</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <Input placeholder="e.g. Software Engineer Resume" value={title} onChange={(e) => setTitle(e.target.value)} />
              <Button onClick={handleCreate} disabled={createResume.isPending}>
                {createResume.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                Create
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map((i) => <Skeleton key={i} className="h-40" />)}
        </div>
      ) : Array.isArray(resumes) && resumes.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {resumes.map((r: any) => (
            <Card key={r.id} className={r.is_active ? "ring-2 ring-primary" : ""}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      {r.title}
                      {r.is_active && <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />}
                    </CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">{r.target_role || "No target role"}</p>
                  </div>
                  <Badge variant={r.is_active ? "success" : "secondary"}>
                    {r.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Skills</span>
                    <span>{(r.skills || []).length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Experience</span>
                    <span>{(r.experience || []).length} entries</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Created</span>
                    <span>{formatDate(r.created_at)}</span>
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  {!r.is_active && (
                    <Button size="sm" variant="outline" onClick={() => setActive.mutate(r.id)} disabled={setActive.isPending}>
                      {setActive.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Star className="h-4 w-4 mr-1" />}
                      Set Active
                    </Button>
                  )}
                  <Button size="sm" variant="ghost">
                    <Upload className="h-4 w-4 mr-1" />Upload
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">
            No resumes yet. Create your first resume profile.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
