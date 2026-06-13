"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Plus, Briefcase, Mail, Globe, Check, AlertCircle, Play, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const MotionTableRow = motion(TableRow);

export default function BusinessesPage() {
  const [businesses, setBusinesses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [search, setSearch] = useState("");
  
  // Form State
  const [form, setForm] = useState({
    name: "",
    category: "",
    location: "",
    website_url: "",
    email: "",
    auto_apply: false
  });

  useEffect(() => {
    fetchBusinesses();
  }, []);

  const fetchBusinesses = async () => {
    try {
      const res = await api.get("/businesses/");
      setBusinesses(res.data.results || res.data || []);
    } catch (error) {
      console.error("Failed to fetch businesses:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleRunPipeline = async (id: string) => {
    try {
      await api.post(`/businesses/${id}/run_pipeline/`);
      alert("Outreach generation pipeline started for this business!");
    } catch (error) {
      console.error("Failed to run pipeline:", error);
      alert("Error starting pipeline.");
    }
  };

  const handleToggleAutoApply = async (id: string, currentStatus: boolean) => {
    try {
      await api.patch(`/businesses/${id}/`, { auto_apply: !currentStatus });
      setBusinesses((prev: any) =>
        prev.map((b: any) => (b.id === id ? { ...b, auto_apply: !currentStatus } : b))
      );
    } catch (error) {
      console.error("Failed to toggle auto-apply:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.category || !form.location) {
      alert("Please fill name, category, and location.");
      return;
    }
    
    try {
      await api.post("/businesses/", form);
      setShowModal(false);
      setForm({
        name: "",
        category: "",
        location: "",
        website_url: "",
        email: "",
        auto_apply: false
      });
      fetchBusinesses();
    } catch (error) {
      console.error("Failed to create business:", error);
      alert("Error creating business. Please verify fields.");
    }
  };

  const filteredBusinesses = businesses.filter((biz: any) => 
    biz.name.toLowerCase().includes(search.toLowerCase()) ||
    biz.category.toLowerCase().includes(search.toLowerCase()) ||
    biz.location.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 relative h-full">
      {/* Page Header */}
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <h1 className="text-3xl font-black tracking-tight text-zinc-50 flex items-center gap-2">
            <Briefcase className="h-7 w-7 text-blue-500 fill-blue-500/10" />
            Target Business Leads
          </h1>
          <p className="text-sm text-zinc-400">
            Manage your targeted local business prospects, customize contact details, and trigger automated outreach.
          </p>
        </div>
        <Button 
          onClick={() => setShowModal(true)} 
          className="flex items-center gap-1.5 shadow-md shadow-blue-500/10 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold border-0 h-10 px-5 rounded-xl transition-all duration-200 hover:scale-[1.01]"
        >
          <Plus className="h-4.5 w-4.5" />
          Add Lead
        </Button>
      </div>

      {/* Filter and Search */}
      <div className="flex items-center space-x-2">
        <Input 
          placeholder="Search leads by name, category, location..." 
          className="max-w-md h-11 bg-zinc-900/30 border-zinc-800 text-zinc-100 placeholder-zinc-500 focus:border-blue-500 focus:ring-blue-500/20 rounded-xl" 
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Business Leads Table */}
      <div className="border border-zinc-800/80 rounded-2xl bg-zinc-900/20 backdrop-blur-md shadow-lg overflow-hidden">
        <Table>
          <TableHeader className="bg-zinc-900/40 border-b border-zinc-800/85">
            <TableRow className="border-b border-zinc-800/80 hover:bg-transparent">
              <TableHead className="font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Company</TableHead>
              <TableHead className="font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Category & Location</TableHead>
              <TableHead className="font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Direct Contact</TableHead>
              <TableHead className="font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Maturity Score</TableHead>
              <TableHead className="font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Auto-Apply</TableHead>
              <TableHead className="text-right font-bold text-zinc-400 py-4 px-6 text-xs uppercase tracking-wider">Pipeline Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-zinc-500 text-sm font-medium">
                  <div className="flex justify-center items-center gap-2">
                    <div className="h-4 w-4 border-2 border-zinc-700 border-t-blue-500 rounded-full animate-spin"></div>
                    Retrieving leads registry...
                  </div>
                </TableCell>
              </TableRow>
            ) : filteredBusinesses.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-zinc-500 text-sm">
                  No businesses found. Click &quot;Add Lead&quot; to begin.
                </TableCell>
              </TableRow>
            ) : (
              filteredBusinesses.map((biz: any, index: number) => (
                <MotionTableRow 
                  key={biz.id} 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, delay: index * 0.03, ease: "easeOut" }}
                  className="border-b border-zinc-800/50 hover:bg-zinc-800/25 transition-all duration-200"
                >
                  <TableCell className="font-bold text-zinc-50 py-5 px-6">
                    {biz.name}
                    {biz.website_url && (
                      <a 
                        href={biz.website_url} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="flex items-center gap-1.5 text-[10px] text-blue-400 font-semibold hover:text-blue-300 hover:underline mt-1.5 w-fit"
                      >
                        <Globe className="h-3 w-3" />
                        {biz.website_url.replace(/^https?:\/\/(www\.)?/, '')}
                      </a>
                    )}
                  </TableCell>
                  <TableCell className="py-5 px-6">
                    <span className="text-sm font-semibold text-zinc-200 block">{biz.category}</span>
                    <span className="text-xs text-zinc-500 font-medium block mt-0.5">{biz.location}</span>
                  </TableCell>
                  <TableCell className="py-5 px-6">
                    {biz.email ? (
                      <span className="text-xs text-zinc-200 flex items-center gap-2 font-mono bg-zinc-950/40 px-2.5 py-1.5 rounded-lg border border-zinc-800/60 w-fit">
                        <Mail className="h-3.5 w-3.5 text-zinc-400" />
                        {biz.email}
                      </span>
                    ) : (
                      <span className="text-[10px] text-zinc-500 italic px-2 py-1 rounded bg-zinc-950/20 border border-dashed border-zinc-800/40">No direct email</span>
                    )}
                  </TableCell>
                  <TableCell className="py-5 px-6">
                    <div className="flex flex-col gap-2">
                      {biz.digital_score > 0 ? (
                        <Badge 
                          variant="outline"
                          className={`text-[10px] font-mono font-bold w-fit px-2 py-0.5 ${
                            biz.digital_score > 70 ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 
                            biz.digital_score > 40 ? 'bg-amber-500/10 text-amber-600 border-amber-500/20' : 
                            'bg-rose-500/10 text-rose-600 border-rose-500/20'
                          }`}
                        >
                          SCORE: {biz.digital_score}/100
                        </Badge>
                      ) : (
                        <span className="text-[10px] text-zinc-500 font-bold bg-zinc-950/20 border border-zinc-800/40 px-2 py-0.5 rounded w-fit">UNANALYZED</span>
                      )}
                      
                      {biz.has_website ? (
                        <span className="text-[9px] text-emerald-400 flex items-center gap-1 font-bold tracking-wider">
                          <Check className="h-3 w-3" />
                          WEBSITE DETECTED
                        </span>
                      ) : (
                        <span className="text-[9px] text-rose-400 flex items-center gap-1 font-bold tracking-wider">
                          <AlertCircle className="h-3 w-3" />
                          NO WEBSITE
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="py-5 px-6">
                    <div className="flex items-center gap-2.5">
                      <button
                        onClick={() => handleToggleAutoApply(biz.id, biz.auto_apply)}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none ${
                          biz.auto_apply ? 'bg-blue-600 shadow-sm shadow-blue-500/25' : 'bg-zinc-800'
                        }`}
                      >
                        <span
                          className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-200 ${
                            biz.auto_apply ? 'translate-x-4.5' : 'translate-x-1'
                          }`}
                        />
                      </button>
                      <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider font-mono">
                        {biz.auto_apply ? "ACTIVE" : "DRAFT"}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right py-5 px-6">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleRunPipeline(biz.id)}
                      className="text-xs font-semibold flex items-center gap-1.5 h-9 ml-auto bg-zinc-900 border-zinc-800 hover:bg-zinc-800 text-zinc-300 hover:text-zinc-50 rounded-xl"
                    >
                      <Play className="h-3 w-3 text-blue-500 fill-blue-500" />
                      Run Flow
                    </Button>
                  </TableCell>
                </MotionTableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Add Lead overlay Modal */}
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
              className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full overflow-hidden shadow-2xl flex flex-col z-10"
            >
              <div className="p-5 border-b border-zinc-800/80 bg-zinc-900/40 flex justify-between items-center">
                <h2 className="font-bold text-zinc-50 flex items-center gap-2 text-sm uppercase tracking-wider font-mono">
                  <Sparkles className="h-4.5 w-4.5 text-blue-500" />
                  Add Lead Prospect
                </h2>
                <button 
                  onClick={() => setShowModal(false)}
                  className="text-zinc-400 hover:text-zinc-200 font-bold text-sm"
                >
                  ✕
                </button>
              </div>
              
              <form onSubmit={handleSubmit} className="p-6 space-y-5 bg-zinc-900/60">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2 col-span-2">
                    <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider font-mono">Business Name *</label>
                    <Input 
                      placeholder="e.g. Apex Health Clinic" 
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-blue-500/20 h-10 rounded-xl"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider font-mono">Category *</label>
                    <Input 
                      placeholder="e.g. Dentist, Lawyer" 
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-blue-500/20 h-10 rounded-xl"
                      value={form.category}
                      onChange={(e) => setForm({ ...form, category: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider font-mono">Location *</label>
                    <Input 
                      placeholder="e.g. Boston, MA" 
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-blue-500/20 h-10 rounded-xl"
                      value={form.location}
                      onChange={(e) => setForm({ ...form, location: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider font-mono">Website URL (Optional)</label>
                    <Input 
                      placeholder="e.g. https://apexhealth.com" 
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-blue-500/20 h-10 rounded-xl"
                      value={form.website_url}
                      onChange={(e) => setForm({ ...form, website_url: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider font-mono">Direct Contact Email (Optional)</label>
                    <Input 
                      type="email"
                      placeholder="e.g. contact@apexhealth.com" 
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-blue-500/20 h-10 rounded-xl"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
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
                    <span className="text-[10px] text-zinc-500 leading-relaxed block mt-0.5">Automatically trigger Playwright contact submissions upon pipeline generation.</span>
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
                    Create Lead
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
