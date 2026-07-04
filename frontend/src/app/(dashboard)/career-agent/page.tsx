"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Bot, Target, Brain, Sparkles, TrendingUp, Loader2 } from "lucide-react";
import api from "@/lib/api";

type Goal = {
  id: string;
  target_titles: string[];
  target_salary_min: number | null;
  target_salary_max: number | null;
  target_companies: string[];
  target_locations: string[];
  remote_preference: string;
  seniority_level: string | null;
  min_skills: string[];
  preferred_skills: string[];
};

type Memory = {
  id: string;
  memory_type: string;
  key: string;
  value: Record<string, unknown>;
  confidence: number;
  source: string | null;
  created_at: string;
};

type Recommendation = {
  recommendations?: Array<{
    action: string;
    reason: string;
    priority: string;
  }>;
  error?: string;
};

export default function CareerAgentPage() {
  const [goals, setGoals] = useState<Goal | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [titleInput, setTitleInput] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/api/v1/ai/goals/").then((r) => {
        const data = r.data as Goal[];
        if (data.length > 0) setGoals(data[0]);
      }).catch(() => {}),
      api.get("/api/v1/ai/memories/").then((r) => {
        setMemories(r.data as Memory[]);
      }).catch(() => {}),
      api.get("/api/v1/ai/agent/recommendations/").then((r) => {
        setRecommendations(r.data as Recommendation);
      }).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const saveGoal = async () => {
    if (!goals) {
      const res = await api.post("/api/v1/ai/goals/", {
        target_titles: titleInput ? [titleInput] : [],
        remote_preference: "any",
      });
      setGoals(res.data as Goal);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-32" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Bot className="h-8 w-8 text-primary" />
            Career Agent
          </h1>
          <p className="text-muted-foreground">Your autonomous AI career assistant</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 pb-2">
            <Target className="h-5 w-5 text-primary" />
            <CardTitle className="text-sm font-medium">Career Goals</CardTitle>
          </CardHeader>
          <CardContent>
            {goals ? (
              <div className="space-y-2 text-sm">
                <p><strong>Titles:</strong> {goals.target_titles?.join(", ") || "Not set"}</p>
                <p><strong>Salary:</strong> {goals.target_salary_min ? `$${goals.target_salary_min.toLocaleString()}` : "?"} – {goals.target_salary_max ? `$${goals.target_salary_max.toLocaleString()}` : "?"}</p>
                <p><strong>Remote:</strong> {goals.remote_preference}</p>
                <p><strong>Seniority:</strong> {goals.seniority_level || "Any"}</p>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Set your career goals to guide the agent</p>
                <div className="flex gap-2">
                  <Input placeholder="e.g. Senior AI Engineer" value={titleInput} onChange={(e) => setTitleInput(e.target.value)} />
                  <Button size="sm" onClick={saveGoal}><Sparkles className="h-4 w-4 mr-1" />Set</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center gap-2 pb-2">
            <Brain className="h-5 w-5 text-primary" />
            <CardTitle className="text-sm font-medium">Agent Memory</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{memories.length}</p>
            <p className="text-xs text-muted-foreground">Learned patterns</p>
            <div className="mt-2 space-y-1">
              {memories.slice(0, 3).map((m) => (
                <div key={m.id} className="text-xs flex items-center gap-1">
                  <Badge variant={m.memory_type === "success_pattern" ? "default" : "secondary"} className="text-[10px] px-1">
                    {m.memory_type === "success_pattern" ? "✅" : "📌"}
                  </Badge>
                  <span className="truncate">{m.key}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center gap-2 pb-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            <CardTitle className="text-sm font-medium">Agent Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-green-500" />
              <span className="text-sm font-medium">Active</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">Ready to discover and apply</p>
            <Progress value={goals ? 75 : 25} className="mt-2 h-1" />
            <p className="text-xs text-muted-foreground mt-1">Goal completion: {goals ? "75%" : "25%"}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            AI Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-16" />
              <Skeleton className="h-16" />
            </div>
          ) : recommendations?.error ? (
            <p className="text-sm text-muted-foreground">Connect a Gemini API key to get recommendations</p>
          ) : recommendations?.recommendations ? (
            <div className="space-y-3">
              {recommendations.recommendations.map((r, i) => (
                <div key={i} className="p-3 border rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge>{r.action}</Badge>
                    <span className="text-xs text-muted-foreground">{r.priority}</span>
                  </div>
                  <p className="text-sm">{r.reason}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Generating recommendations...</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
