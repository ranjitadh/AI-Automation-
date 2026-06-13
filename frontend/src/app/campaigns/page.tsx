"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Plus, Users, Play, Calendar, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const MotionTableRow = motion(TableRow);

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  
  // Form state
  const [form, setForm] = useState({
    name: "",
    target_category: "",
    auto_apply: false
  });

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      const res = await api.get("/campaigns/");
      setCampaigns(res.data.results || res.data || []);
    } catch (error) {
      console.error("Failed to fetch campaigns:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleRunCampaign = async (id: string) => {
    try {
      const res = await api.post(`/campaigns/${id}/run/`);
      alert(`Campaign queued! Pipelines triggered for ${res.data.businesses_queued} matching businesses.`);
      fetchCampaigns();
    } catch (error) {
      console.error("Failed to run campaign:", error);
      alert("Error starting campaign.");
    }
  };

  const handleToggleAutoApply = async (id: string, currentStatus: boolean) => {
    try {
      await api.patch(`/campaigns/${id}/`, { auto_apply: !currentStatus });
      setCampaigns((prev: any) =>
        prev.map((c: any) => (c.id === id ? { ...c, auto_apply: !currentStatus } : c))
      );
    } catch (error) {
      console.error("Failed to toggle campaign auto-apply:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name) {
      alert("Please fill campaign name.");
      return;
    }
    
    try {
      await api.post("/campaigns/", form);
      setShowModal(false);
      setForm({
        name: "",
        target_category: "",
        auto_apply: false
      });
      fetchCampaigns();
    } catch (error) {
      console.error("Failed to create campaign:", error);
      alert("Error creating campaign.");
    }
  };

  return (
    <div className="space-y-6 relative h-full">
      {/* Page Header */}
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <h1 className="text-3xl font-black tracking-tight text-zinc-50 flex items-center gap-2">
            <Users className="h-7 w-7 text-blue-500 fill-blue-500/10" />
            Outreach Campaigns
          </h1>
          <p className="text-sm text-zinc-400">
            Target specific local business sectors, schedule automated direct applies, and manage campaign pipeline telemetry.
          </p>
        </div>
        <Button 
          onClick={() => setShowModal(true)} 
          className="flex items-center gap-1.5 shadow-md shadow-blue-500/10 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold border-0 h-10 px-5 rounded-xl transition-all duration-200 hover:scale-[1.01]"
        >
          <Plus className="h-4.5 w-4.5" />
          Create Campaign
        </Button>
      </div>

      {/* Campaigns Command Registry */}
      <div className="border border-zinc-800/80 rounded-2xl bg-zinc-900/20 backdrop-blur-md shadow-lg overflow-hidden">
        <Table>
          <TableHeader className="bg-zinc-900/40 border-b border-zinc-800/85">
            <TableRow className="border-b border-zinc-800/80 hover:bg-transparent">
              <TableHead className="font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Campaign Name</TableHead>
              <TableHead className="font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Target Industry</TableHead>
              <TableHead className="font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Auto-Apply Setting</TableHead>
              <TableHead className="font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Status</TableHead>
              <TableHead className="font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Created Date</TableHead>
              <TableHead className="text-right font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Execution</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-zinc-500 text-sm font-medium">
                  <div className="flex justify-center items-center gap-2">
                    <div className="h-4 w-4 border-2 border-zinc-700 border-t-blue-500 rounded-full animate-spin"></div>
                    Retrieving campaigns...
                  </div>
                </TableCell>
              </TableRow>
            ) : campaigns.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-zinc-500 text-sm">
                  No outreach campaigns scheduled. Click &quot;Create Campaign&quot; to begin.
                </TableCell>
              </TableRow>
            ) : (
              campaigns.map((camp: any, index: number) => (
                <MotionTableRow 
                  key={camp.id} 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, delay: index * 0.03, ease: "easeOut" }}
                  className="border-b border-zinc-800/50 hover:bg-zinc-800/25 transition-all duration-200"
                >
                  <TableCell className="font-bold text-zinc-50 py-5 px-6">
                    {camp.name}
                  </TableCell>
                  <TableCell className="py-5 px-6">
                    <Badge variant="outline" className="bg-blue-500/5 text-blue-400 border-blue-500/15 text-[10px] font-mono font-bold tracking-wider px-2.5 py-0.5 rounded-lg">
                      {camp.target_category ? camp.target_category.toUpperCase() : "ALL LEADS"}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-5 px-6">
                    <div className="flex items-center gap-2.5">
                      <button
                        onClick={() => handleToggleAutoApply(camp.id, camp.auto_apply)}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none ${
                          camp.auto_apply ? 'bg-blue-600 shadow-sm shadow-blue-500/25' : 'bg-zinc-800'
                        }`}
                      >
                        <span
                          className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-200 ${
                            camp.auto_apply ? 'translate-x-4.5' : 'translate-x-1'
                          }`}
                        />
                      </button>
                      <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider font-mono">
                        {camp.auto_apply ? "AUTO MODE" : "DRAFT MODE"}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="py-5 px-6">
                    <Badge 
                      variant={camp.status === 'active' ? 'default' : 'secondary'}
                      className={`text-[9px] font-bold font-mono px-2 py-0.5 rounded ${
                        camp.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 
                        camp.status === 'completed' ? 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20' : 
                        'bg-zinc-950/20 border border-zinc-800/40 text-zinc-400'
                      }`}
                    >
                      {camp.status.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-5 px-6 text-zinc-500 text-xs font-semibold">
                    <span className="flex items-center gap-2">
                      <Calendar className="h-3.5 w-3.5 text-zinc-400" />
                      {new Date(camp.created_at).toLocaleDateString()}
                    </span>
                  </TableCell>
                  <TableCell className="text-right py-5 px-6">
                    <Button 
                      variant="default" 
                      size="sm" 
                      onClick={() => handleRunCampaign(camp.id)}
                      disabled={camp.status === 'active'}
                      className="text-xs font-semibold flex items-center gap-1.5 h-9 ml-auto bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-zinc-900 disabled:to-zinc-900 text-white border-0 rounded-xl transition-all duration-200"
                    >
                      <Play className="h-3 w-3 text-white fill-white" />
                      Run Campaign
                    </Button>
                  </TableCell>
                </MotionTableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create Campaign overlay Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 bg-zinc-950/80 z-50 flex items-center justify-center p-4 backdrop-blur-md">
            {/* Backdrop Fade */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-zinc-950/20"
              onClick={() => setShowModal(false)}
            />

            {/* Container Spring Modal */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ type: "spring", stiffness: 350, damping: 28 }}
              className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full overflow-hidden shadow-2xl flex flex-col z-10"
            >
              <div className="p-5 border-b border-zinc-800/80 bg-zinc-900/40 flex justify-between items-center">
                <h2 className="font-bold text-zinc-50 flex items-center gap-2 text-sm uppercase tracking-wider font-mono">
                  <Sparkles className="h-4.5 w-4.5 text-blue-500" />
                  Create Campaign
                </h2>
                <button 
                  onClick={() => setShowModal(false)}
                  className="text-zinc-400 hover:text-zinc-200 font-bold text-sm"
                >
                  ✕
                </button>
              </div>
              
              <form onSubmit={handleSubmit} className="p-6 space-y-5 bg-zinc-900/60">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider font-mono">Campaign Name *</label>
                    <Input 
                      placeholder="e.g. Q2 Chiropractors Campaign" 
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-blue-500/20 h-10 rounded-xl"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider font-mono">Target Industry Category (Optional)</label>
                    <Input 
                      placeholder="e.g. Chiropractor (leave blank to target all)" 
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-blue-500/20 h-10 rounded-xl"
                      value={form.target_category}
                      onChange={(e) => setForm({ ...form, target_category: e.target.value })}
                    />
                  </div>
                </div>

                {/* Glassmorphic Switch Info Container */}
                <div className="flex items-center space-x-3 bg-zinc-950/45 p-4 rounded-xl border border-zinc-800/80 mt-2">
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, auto_apply: !form.auto_apply })}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none ${
                      form.auto_apply ? 'bg-blue-600 shadow-sm shadow-blue-500/20' : 'bg-zinc-800'
                    }`}
                  >
                    <span
                      className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-200 ${
                        form.auto_apply ? 'translate-x-4.5' : 'translate-x-1'
                      }`}
                    />
                  </button>
                  <div className="space-y-0.5">
                    <span className="text-[11px] font-bold text-zinc-200 uppercase tracking-wider font-mono block">Enable Direct Auto-Apply</span>
                    <span className="text-[10px] text-zinc-500 leading-relaxed block mt-0.5">Automatically trigger Playwright contact submissions upon pipeline execution.</span>
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-5 border-t border-zinc-800/80">
                  <Button 
                    type="button" 
                    variant="outline" 
                    onClick={() => setShowModal(false)}
                    className="text-xs font-semibold bg-zinc-900 border-zinc-800 hover:bg-zinc-800 text-zinc-300 rounded-xl h-10"
                  >
                    Cancel
                  </Button>
                  <Button 
                    type="submit"
                    className="text-xs font-semibold shadow-md shadow-blue-500/10 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white border-0 h-10 px-5 rounded-xl transition-all duration-200"
                  >
                    Create Campaign
                  </Button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
