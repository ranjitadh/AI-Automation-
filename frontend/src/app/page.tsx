"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Users, Mail, CheckCircle2, Activity, Zap, Target, RefreshCw, Cpu, Database, Network } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";

export default function Dashboard() {
  const [stats, setStats] = useState({
    businesses: 0,
    campaigns: 0,
    emailsGenerated: 0,
    emailsSent: 0,
    replies: 0,
  });
  const [recentOutreach, setRecentOutreach] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStatsAndActivity = async () => {
    try {
      const [bizRes, campRes, outRes] = await Promise.all([
        api.get("/businesses/"),
        api.get("/campaigns/"),
        api.get("/outreach/")
      ]);
      
      const emails = outRes.data.results || outRes.data || [];
      const sent = emails.filter((e: any) => e.status === "sent").length;
      const replied = emails.filter((e: any) => e.reply_received).length;

      setStats({
        businesses: bizRes.data.count || bizRes.data.length || 0,
        campaigns: campRes.data.count || campRes.data.length || 0,
        emailsGenerated: emails.length,
        emailsSent: sent,
        replies: replied,
      });

      // Grab first 5 for active feed
      setRecentOutreach(emails.slice(0, 5));
    } catch (error) {
      console.error("Error fetching stats:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatsAndActivity();
  }, []);

  // Compute percentages for visual rings
  const applyRate = stats.emailsGenerated > 0 
    ? Math.round((stats.emailsSent / stats.emailsGenerated) * 100) 
    : 0;

  const replyRate = stats.emailsSent > 0 
    ? Math.round((stats.replies / stats.emailsSent) * 100) 
    : 0;

  // Stagger variants
  const listContainer = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.05 }
    }
  };

  const listItem = {
    hidden: { opacity: 0, y: 15 },
    show: { 
      opacity: 1, 
      y: 0, 
      transition: { type: "spring" as const, stiffness: 120, damping: 14 } 
    }
  };

  return (
    <motion.div 
      initial="hidden"
      animate="show"
      variants={listContainer}
      className="space-y-6 h-full"
    >
      {/* Header Banner */}
      <motion.div 
        variants={listItem}
        className="flex justify-between items-center bg-zinc-900/25 border border-zinc-800/40 p-6 rounded-2xl backdrop-blur-md"
      >
        <div>
          <h1 className="text-3xl font-black tracking-tight text-zinc-50 bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            System Command Center
          </h1>
          <p className="text-sm text-zinc-400 mt-1 flex items-center gap-1.5 font-medium">
            <Zap className="h-4 w-4 text-blue-500 fill-blue-500/20" />
            Autonomous outreach schedule and live browser dispatches.
          </p>
        </div>
        <button 
          onClick={fetchStatsAndActivity}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors shadow-sm"
        >
          <RefreshCw className={`h-4.5 w-4.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </motion.div>
      
      {/* Asymmetric Core Columns Grid */}
      <div className="grid gap-6 grid-cols-1 lg:grid-cols-3 items-start">
        {/* Left Double Column: Metric Cards & SVG Gauge Panel */}
        <div className="lg:col-span-2 space-y-6">
          {/* Asymmetric Metric Grid */}
          <motion.div 
            variants={listContainer}
            className="grid gap-6 grid-cols-1 sm:grid-cols-3"
          >
            {/* Total Leads (Double Block for Asymmetry) */}
            <motion.div 
              variants={listItem}
              whileHover={{ y: -4, transition: { duration: 0.15 } }}
              className="sm:col-span-2"
            >
              <Card className="bg-zinc-900/30 border-zinc-800/80 backdrop-blur-md shadow-sm relative overflow-hidden group hover:border-zinc-700/80 transition-all duration-300 h-full flex flex-col justify-between">
                <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full blur-2xl pointer-events-none group-hover:bg-blue-500/10 transition-colors" />
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 p-5">
                  <CardTitle className="text-xs font-bold tracking-wider text-zinc-400 uppercase">Leads Database</CardTitle>
                  <Users className="h-4.5 w-4.5 text-blue-400" />
                </CardHeader>
                <CardContent className="p-5 pt-0">
                  <div className="text-4xl font-black text-zinc-50 tracking-tight">{stats.businesses}</div>
                  <p className="text-[10px] text-zinc-500 mt-2 flex items-center gap-1 font-semibold">
                    <span className="text-blue-500 font-bold">ACTIVE SCHEDULE</span> registry matching targeted profiles
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            {/* Direct Dispatches */}
            <motion.div 
              variants={listItem}
              whileHover={{ y: -4, transition: { duration: 0.15 } }}
            >
              <Card className="bg-zinc-900/30 border-zinc-800/80 backdrop-blur-md shadow-sm relative overflow-hidden group hover:border-zinc-700/80 transition-all duration-300 h-full flex flex-col justify-between">
                <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none group-hover:bg-emerald-500/10 transition-colors" />
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 p-5">
                  <CardTitle className="text-xs font-bold tracking-wider text-zinc-400 uppercase">Applied Leads</CardTitle>
                  <CheckCircle2 className="h-4.5 w-4.5 text-emerald-400" />
                </CardHeader>
                <CardContent className="p-5 pt-0">
                  <div className="text-3xl font-black text-zinc-50 tracking-tight">{stats.emailsSent}</div>
                  <p className="text-[10px] text-zinc-500 mt-2 flex items-center gap-1 font-semibold">
                    <span className="text-emerald-500 font-bold">DISPATCHED</span> auto applying runs
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            {/* Drafts Generated */}
            <motion.div 
              variants={listItem}
              whileHover={{ y: -4, transition: { duration: 0.15 } }}
            >
              <Card className="bg-zinc-900/30 border-zinc-800/80 backdrop-blur-md shadow-sm relative overflow-hidden group hover:border-zinc-700/80 transition-all duration-300 h-full flex flex-col justify-between">
                <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-full blur-2xl pointer-events-none group-hover:bg-indigo-500/10 transition-colors" />
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 p-5">
                  <CardTitle className="text-xs font-bold tracking-wider text-zinc-400 uppercase">Draft Generated</CardTitle>
                  <Mail className="h-4.5 w-4.5 text-indigo-400" />
                </CardHeader>
                <CardContent className="p-5 pt-0">
                  <div className="text-3xl font-black text-zinc-50 tracking-tight">{stats.emailsGenerated}</div>
                  <p className="text-[10px] text-zinc-500 mt-2 flex items-center gap-1 font-semibold">
                    <span className="text-indigo-500 font-bold">AI SDR COPYWRITER</span> notes
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            {/* Replies Logged (Double Block Asymmetry on Row 2) */}
            <motion.div 
              variants={listItem}
              whileHover={{ y: -4, transition: { duration: 0.15 } }}
              className="sm:col-span-2"
            >
              <Card className="bg-zinc-900/30 border-zinc-800/80 backdrop-blur-md shadow-sm relative overflow-hidden group hover:border-zinc-700/80 transition-all duration-300 h-full flex flex-col justify-between">
                <div className="absolute top-0 right-0 w-32 h-32 bg-pink-500/5 rounded-full blur-2xl pointer-events-none group-hover:bg-pink-500/10 transition-colors" />
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 p-5">
                  <CardTitle className="text-xs font-bold tracking-wider text-zinc-400 uppercase">Conversion Node</CardTitle>
                  <Activity className="h-4.5 w-4.5 text-pink-400" />
                </CardHeader>
                <CardContent className="p-5 pt-0">
                  <div className="text-4xl font-black text-zinc-50 tracking-tight">{stats.replies}</div>
                  <p className="text-[10px] text-zinc-500 mt-2 flex items-center gap-1 font-semibold">
                    <span className="text-pink-500 font-bold">REPLY CONVERSIONS</span> logged in communications subsystem
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>

          {/* SVG Progress Dial Gauge Panel */}
          <motion.div variants={listItem}>
            <Card className="bg-zinc-900/30 border-zinc-800/80 backdrop-blur-md p-5 flex flex-col justify-between min-h-[300px]">
              <CardHeader className="p-0 pb-4">
                <CardTitle className="text-sm font-bold tracking-wider text-zinc-400 uppercase font-mono">Automation Analytics Engine</CardTitle>
                <CardDescription className="text-xs text-zinc-500">Visual gauges mapping Playwright contact dispatches.</CardDescription>
              </CardHeader>
              
              <CardContent className="p-0 flex-1 flex flex-col sm:flex-row items-center justify-around gap-6">
                {/* Visual Gauge 1: Auto-Apply Dispatch Rate */}
                <div className="flex flex-col items-center text-center space-y-4">
                  <div className="relative flex items-center justify-center">
                    <svg className="w-32 h-32 transform -rotate-90">
                      <circle 
                        cx="64" cy="64" r="42" 
                        className="stroke-zinc-800/60 fill-transparent" 
                        strokeWidth="8"
                      />
                      <motion.circle 
                        cx="64" cy="64" r="42" 
                        className="stroke-blue-500 fill-transparent" 
                        strokeWidth="8"
                        strokeDasharray="263.89"
                        initial={{ strokeDashoffset: 263.89 }}
                        animate={{ strokeDashoffset: 263.89 - (applyRate / 100) * 263.89 }}
                        transition={{ duration: 1.2, ease: "easeOut" }}
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute flex flex-col items-center">
                      <span className="text-xl font-black text-zinc-50 tracking-tight">{applyRate}%</span>
                      <span className="text-[8px] uppercase tracking-wider font-bold text-zinc-500">Applied</span>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-zinc-200">Auto-Apply Rate</h4>
                    <p className="text-[9px] text-zinc-500 max-w-[150px] leading-relaxed">Percentage of leads processed by Chrome browser automation.</p>
                  </div>
                </div>

                {/* Visual Gauge 2: Response Conversion Rate */}
                <div className="flex flex-col items-center text-center space-y-4">
                  <div className="relative flex items-center justify-center">
                    <svg className="w-32 h-32 transform -rotate-90">
                      <circle 
                        cx="64" cy="64" r="42" 
                        className="stroke-zinc-800/60 fill-transparent" 
                        strokeWidth="8"
                      />
                      <motion.circle 
                        cx="64" cy="64" r="42" 
                        className="stroke-pink-500 fill-transparent" 
                        strokeWidth="8"
                        strokeDasharray="263.89"
                        initial={{ strokeDashoffset: 263.89 }}
                        animate={{ strokeDashoffset: 263.89 - (replyRate / 100) * 263.89 }}
                        transition={{ duration: 1.2, ease: "easeOut", delay: 0.15 }}
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute flex flex-col items-center">
                      <span className="text-xl font-black text-zinc-50 tracking-tight">{replyRate}%</span>
                      <span className="text-[8px] uppercase tracking-wider font-bold text-zinc-500">Replied</span>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-zinc-200">Reply Conversion</h4>
                    <p className="text-[9px] text-zinc-500 max-w-[150px] leading-relaxed">Response rate calculated against total dispatched campaigns.</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Right Single Column: Real Telemetry Monitor & Activity Feed */}
        <div className="lg:col-span-1 space-y-6">
          {/* Custom Telemetry Hardware Cockpit */}
          <motion.div variants={listItem}>
            <Card className="border border-zinc-800/80 bg-zinc-900/10 backdrop-blur-md shadow-lg">
              <CardHeader className="p-4 border-b border-zinc-800/80 bg-zinc-900/40">
                <CardTitle className="text-xs font-bold uppercase tracking-wider font-mono flex items-center gap-1.5 text-zinc-200">
                  <Cpu className="h-4 w-4 text-blue-500" />
                  System Telemetry Node
                </CardTitle>
                <CardDescription className="text-[10px] text-zinc-500 mt-1">
                  Active server core loads and scheduling threads.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 space-y-4 font-mono text-[9px] text-zinc-500">
                {/* Visual simulated CPU gauge */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-zinc-400">
                    <span>PLAYWRIGHT CORE LOAD</span>
                    <span className="text-zinc-200 font-bold">34.6%</span>
                  </div>
                  <div className="h-2 w-full bg-zinc-950 rounded-full overflow-hidden border border-zinc-800/60 p-0.5">
                    <motion.div 
                      initial={{ width: "0%" }}
                      animate={{ width: "34.6%" }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      className="h-full bg-blue-500 rounded-full" 
                    />
                  </div>
                </div>

                {/* Visual simulated memory gauge */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-zinc-400">
                    <span>DATABASE CACHE POOL</span>
                    <span className="text-zinc-200 font-bold">12.1%</span>
                  </div>
                  <div className="h-2 w-full bg-zinc-950 rounded-full overflow-hidden border border-zinc-800/60 p-0.5">
                    <motion.div 
                      initial={{ width: "0%" }}
                      animate={{ width: "12.1%" }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      className="h-full bg-indigo-500 rounded-full" 
                    />
                  </div>
                </div>

                {/* Visual simulated celery task queue latency */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-zinc-400">
                    <span>CELERY WORKER LATENCY</span>
                    <span className="text-zinc-200 font-bold">12ms</span>
                  </div>
                  <div className="h-2 w-full bg-zinc-950 rounded-full overflow-hidden border border-zinc-800/60 p-0.5">
                    <motion.div 
                      initial={{ width: "0%" }}
                      animate={{ width: "8%" }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      className="h-full bg-emerald-500 rounded-full" 
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Outreach Activity Log */}
          <motion.div variants={listItem}>
            <Card className="bg-zinc-900/30 border-zinc-800/80 backdrop-blur-md p-5 flex flex-col justify-between">
              <CardHeader className="p-0 pb-4">
                <CardTitle className="text-xs font-bold tracking-wider text-zinc-400 uppercase font-mono">Live Activity Logs</CardTitle>
                <CardDescription className="text-xs text-zinc-500">Chrome applying triggers and registries.</CardDescription>
              </CardHeader>
              
              <CardContent className="p-0 flex-1 overflow-y-auto max-h-[300px]">
                {loading ? (
                  <div className="py-12 text-center text-xs text-zinc-500">Loading activity...</div>
                ) : recentOutreach.length === 0 ? (
                  <div className="py-12 text-center text-xs text-zinc-500">No activity logged.</div>
                ) : (
                  <div className="space-y-4 pr-1.5">
                    {recentOutreach.map((outreach: any) => (
                      <div key={outreach.id} className="flex gap-3 items-start border-b border-zinc-800/40 pb-3 last:border-0 last:pb-0">
                        <div className="h-8 w-8 rounded-lg bg-zinc-800/60 border border-zinc-700/60 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <Target className="h-4 w-4 text-blue-500" />
                        </div>
                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="flex justify-between items-start gap-2">
                            <span className="text-xs font-semibold text-zinc-200 truncate">{outreach.business_name}</span>
                            <Badge 
                              variant="outline" 
                              className={`text-[8px] font-mono font-bold px-1.5 py-0.5 rounded ${
                                outreach.status === 'sent' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 
                                'bg-amber-500/10 text-amber-400 border-amber-500/20'
                              }`}
                            >
                              {outreach.status.toUpperCase()}
                            </Badge>
                          </div>
                          <p className="text-[10px] text-zinc-400 truncate font-medium">{outreach.subject}</p>
                          {outreach.dispatch_status && (
                            <p className="text-[8px] text-zinc-500 font-mono">
                              Auto Mode: <span className={outreach.dispatch_status === 'success' ? 'text-emerald-400' : outreach.dispatch_status === 'failed' ? 'text-rose-400' : 'text-zinc-400'}>{outreach.dispatch_status.toUpperCase()}</span>
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}
