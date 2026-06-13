"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { 
  Rocket, 
  Terminal, 
  CheckCircle2, 
  AlertCircle, 
  Maximize2, 
  RefreshCw, 
  Mail, 
  Send,
  Eye,
  FileText,
  Activity,
  ChevronRight
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function OutreachPage() {
  const [emails, setEmails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEmail, setSelectedEmail] = useState<any>(null);
  const [polling, setPolling] = useState(false);
  const [showScreenshotModal, setShowScreenshotModal] = useState(false);

  useEffect(() => {
    fetchEmails();
  }, []);

  // Poll selected email if it's currently running direct apply
  useEffect(() => {
    let interval: any;
    if (selectedEmail && (selectedEmail.dispatch_status === 'running' || selectedEmail.dispatch_status === 'pending')) {
      setPolling(true);
      interval = setInterval(async () => {
        try {
          const res = await api.get(`/outreach/${selectedEmail.id}/`);
          const updatedEmail = res.data;
          
          // Update selected email
          setSelectedEmail(updatedEmail);
          
          // Update email in the list
          setEmails(prev => prev.map(e => e.id === updatedEmail.id ? updatedEmail : e));
          
          if (updatedEmail.dispatch_status !== 'running' && updatedEmail.dispatch_status !== 'pending') {
            setPolling(false);
            clearInterval(interval);
          }
        } catch (error) {
          console.error("Error polling email status:", error);
          setPolling(false);
          clearInterval(interval);
        }
      }, 2000);
    } else {
      setPolling(false);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [selectedEmail?.id, selectedEmail?.dispatch_status]);

  const fetchEmails = async () => {
    try {
      const res = await api.get("/outreach/");
      const fetchedEmails = res.data.results || res.data || [];
      setEmails(fetchedEmails);
      
      // If selectedEmail exists, update it in the view
      if (selectedEmail) {
        const current = fetchedEmails.find((e: any) => e.id === selectedEmail.id);
        if (current) setSelectedEmail(current);
      }
    } catch (error) {
      console.error("Failed to fetch emails:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkSent = async (id: string) => {
    try {
      await api.patch(`/outreach/${id}/mark_sent/`);
      fetchEmails();
    } catch (error) {
      console.error("Failed to mark as sent:", error);
    }
  };

  const handleRunAutoApply = async (id: string) => {
    try {
      setSelectedEmail((prev: any) => prev ? { ...prev, dispatch_status: 'pending', dispatch_log: '[System] Scheduling direct dispatch...' } : null);
      await api.post(`/outreach/${id}/dispatch_direct/`);
      fetchEmails();
    } catch (error) {
      console.error("Failed to run direct apply model:", error);
    }
  };

  const getScreenshotUrl = (path: string) => {
    if (!path) return "";
    if (path.startsWith("http")) return path;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
    const baseUrl = apiUrl.replace(/\/api$/, "");
    return `${baseUrl}${path}`;
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 h-[85vh] relative">
      {/* Sidebar Queue List */}
      <div className="xl:col-span-1 border border-zinc-800 rounded-2xl bg-zinc-900/20 backdrop-blur-md overflow-hidden flex flex-col h-full shadow-lg">
        <div className="p-4 border-b border-zinc-800/80 bg-zinc-900/40 flex justify-between items-center">
          <h2 className="font-bold text-xs uppercase tracking-wider font-mono text-zinc-100 flex items-center gap-2">
            <Mail className="h-4 w-4 text-blue-500 fill-blue-500/10" />
            Outreach Queue
          </h2>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-zinc-50 hover:bg-zinc-800/50" onClick={fetchEmails}>
            <RefreshCw className={`h-4 w-4 ${polling ? 'animate-spin' : ''}`} />
          </Button>
        </div>
        
        <div className="flex-1 overflow-y-auto divide-y divide-zinc-800/40">
          {loading ? (
            <div className="p-8 text-center text-zinc-500 text-xs font-medium">Loading outreach list...</div>
          ) : emails.length === 0 ? (
            <div className="p-8 text-center text-zinc-500 text-xs">No outreach generated yet.</div>
          ) : (
            emails.map((email: any) => (
              <div 
                key={email.id} 
                className={`p-4 cursor-pointer hover:bg-zinc-800/20 transition-all duration-200 border-l-2 ${
                  selectedEmail?.id === email.id 
                    ? 'bg-zinc-800/30 border-blue-500 shadow-inner' 
                    : 'border-transparent hover:border-zinc-700'
                }`}
                onClick={() => setSelectedEmail(email)}
              >
                <div className="flex justify-between items-start mb-2 gap-2">
                  <span className="font-bold text-[10px] text-zinc-400 font-mono tracking-wide uppercase truncate max-w-[120px]">{email.business_name}</span>
                  <Badge 
                    variant={email.status === 'sent' ? 'default' : email.status === 'replied' ? 'secondary' : 'outline'} 
                    className={`text-[9px] font-bold font-mono px-1.5 py-0 rounded ${
                      email.status === 'sent' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 
                      email.status === 'replied' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' : 
                      'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    {email.status.toUpperCase()}
                  </Badge>
                </div>
                <div className="text-xs font-bold text-zinc-100 truncate mb-1.5 leading-relaxed">
                  {email.subject}
                </div>
                <div className="text-[10px] text-zinc-500 truncate leading-relaxed">
                  {email.email_body}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Details View Area */}
      <div className="xl:col-span-3 flex flex-col xl:flex-row gap-6 h-full overflow-hidden">
        {selectedEmail ? (
          <>
            {/* Outreach Draft Card */}
            <Card className="flex-1 flex flex-col border border-zinc-800/80 bg-zinc-900/10 backdrop-blur-md shadow-lg overflow-hidden h-full">
              <CardHeader className="border-b border-zinc-800 bg-zinc-900/20 p-5">
                <div className="flex justify-between items-start gap-4">
                  <div className="space-y-1.5">
                    <CardTitle className="text-base font-extrabold tracking-tight text-zinc-50 leading-snug">{selectedEmail.subject}</CardTitle>
                    <CardDescription className="text-xs font-semibold text-zinc-400 flex items-center gap-1.5">
                      Recipient: <span className="font-bold text-zinc-200">{selectedEmail.business_name}</span>
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      variant="outline"
                      size="sm"
                      onClick={() => handleMarkSent(selectedEmail.id)}
                      disabled={selectedEmail.status === 'sent' || selectedEmail.status === 'replied'}
                      className="text-xs font-semibold flex items-center gap-1.5 h-9 bg-zinc-900 border-zinc-800 hover:bg-zinc-800 text-zinc-300 hover:text-zinc-50 rounded-xl"
                    >
                      <Send className="h-3 w-3 text-zinc-400" />
                      Mark Sent
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 p-6 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-zinc-300 font-sans border-t border-zinc-900/10">
                {selectedEmail.email_body}
              </CardContent>
            </Card>

            {/* Auto Apply Automation Column */}
            <div className="w-full xl:w-96 flex flex-col gap-6 h-full overflow-y-auto pr-1">
              {/* Telemetry Control Panel */}
              <Card className="border border-zinc-800/80 bg-zinc-900/10 backdrop-blur-md shadow-lg">
                <CardHeader className="p-4 border-b border-zinc-800 bg-zinc-900/20">
                  <CardTitle className="text-xs font-bold uppercase tracking-wider font-mono flex items-center justify-between text-zinc-100">
                    <span className="flex items-center gap-2">
                      <Rocket className="h-4 w-4 text-blue-500 fill-blue-500/10" />
                      Auto Apply Submitter
                    </span>
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                    </span>
                  </CardTitle>
                  <CardDescription className="text-[10px] text-zinc-500 mt-1">
                    Direct automated dispatch scheduling via Headless Playwright engine.
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-4 space-y-4">
                  {selectedEmail.dispatch_status === 'pending' || selectedEmail.dispatch_status === 'running' ? (
                    <div className="flex flex-col items-center justify-center py-6 text-center space-y-3 bg-zinc-950/20 rounded-xl border border-zinc-800/40">
                      <div className="relative">
                        <div className="h-10 w-10 border-4 border-blue-500/10 border-t-blue-500 rounded-full animate-spin"></div>
                        <Activity className="h-4 w-4 text-blue-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
                      </div>
                      <div className="space-y-1">
                        <p className="text-[11px] font-bold text-zinc-200 font-mono">AUTOMATION EXECUTING</p>
                        <p className="text-[9px] text-zinc-500 font-medium">Headless Chrome filling forms...</p>
                      </div>
                    </div>
                  ) : selectedEmail.dispatch_status === 'success' ? (
                    <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-xl text-emerald-400">
                      <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
                      <div>
                        <p className="text-[11px] font-bold uppercase tracking-wider font-mono">SUBMISSION SUCCESSFUL</p>
                        <p className="text-[9px] text-emerald-400/80 font-medium mt-0.5">Outreach successfully submitted.</p>
                      </div>
                    </div>
                  ) : selectedEmail.dispatch_status === 'failed' ? (
                    <div className="flex items-center gap-3 bg-rose-500/10 border border-rose-500/20 p-4 rounded-xl text-rose-400">
                      <AlertCircle className="h-5 w-5 flex-shrink-0" />
                      <div>
                        <p className="text-[11px] font-bold uppercase tracking-wider font-mono">DISPATCH FAILED</p>
                        <p className="text-[9px] text-rose-400/80 font-medium mt-0.5">Review diagnostic logs to troubleshoot.</p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4 py-1">
                      <div className="text-[10px] text-zinc-500 leading-relaxed bg-zinc-950/45 p-3 rounded-xl border border-zinc-800/80 font-medium">
                        Model launches a background Chrome instance to navigate, discover contact forms, and submit outreach.
                      </div>
                      <Button 
                        onClick={() => handleRunAutoApply(selectedEmail.id)}
                        className="w-full text-xs font-semibold flex items-center justify-center gap-2 h-10 shadow-md shadow-blue-500/20 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white border-0 rounded-xl transition-all duration-200 hover:scale-[1.01]"
                      >
                        <Rocket className="h-4 w-4" />
                        Run Auto Apply Model
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Progress Console (Styled with Terminal Header Circles) */}
              {selectedEmail.dispatch_log && (
                <Card className="border border-zinc-800/80 bg-zinc-950 shadow-2xl overflow-hidden flex flex-col flex-1">
                  {/* Decorative Terminal Dot Controls */}
                  <div className="p-3 bg-zinc-900 border-b border-zinc-800/80 flex justify-between items-center">
                    <div className="flex items-center gap-1.5">
                      <div className="h-2.5 w-2.5 rounded-full bg-rose-500/80 shadow shadow-rose-500/20" />
                      <div className="h-2.5 w-2.5 rounded-full bg-amber-500/80 shadow shadow-amber-500/20" />
                      <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/80 shadow shadow-emerald-500/20" />
                      <span className="text-[10px] font-mono font-bold text-zinc-400 ml-2 uppercase flex items-center gap-1">
                        <Terminal className="h-3 w-3 text-blue-400" />
                        apply_diagnostics.sh
                      </span>
                    </div>
                    <Badge variant="outline" className="text-[8px] px-1.5 font-mono uppercase bg-zinc-950 border-zinc-800 text-zinc-500 font-bold tracking-wider">
                      {selectedEmail.dispatch_status}
                    </Badge>
                  </div>
                  
                  {/* Log Printout */}
                  <div className="p-4 font-mono text-[9px] overflow-y-auto leading-relaxed flex-1 h-48 text-zinc-300 space-y-2 select-all">
                    {selectedEmail.dispatch_log.split("\n").map((logLine: string, index: number) => {
                      let colorClass = "text-zinc-400";
                      
                      if (logLine.startsWith("[Success]")) {
                        colorClass = "text-emerald-400 font-bold";
                      } else if (logLine.startsWith("[Error]") || logLine.startsWith("[Failed]")) {
                        colorClass = "text-rose-400 font-bold";
                      } else if (logLine.startsWith("[System]")) {
                        colorClass = "text-blue-400 font-bold";
                      } else if (logLine.startsWith("[Warning]")) {
                        colorClass = "text-amber-400 font-medium";
                      } else if (logLine.startsWith("[1/4]") || logLine.startsWith("[2/4]") || logLine.startsWith("[3/4]") || logLine.startsWith("[4/4]")) {
                        colorClass = "text-zinc-50 font-bold";
                      }
                      
                      return (
                        <div key={index} className={`${colorClass} flex items-start gap-1 break-all whitespace-pre-wrap`}>
                          <ChevronRight className="h-3 w-3 text-zinc-600 flex-shrink-0 mt-0.5" />
                          <span>{logLine}</span>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              )}

              {/* Screenshot Verification Screen proof */}
              {selectedEmail.screenshot && (
                <Card className="border border-zinc-800/80 bg-zinc-900/10 backdrop-blur-md shadow-lg overflow-hidden relative group">
                  <div className="absolute inset-0 bg-gradient-to-t from-zinc-950/20 to-transparent pointer-events-none" />
                  <div className="p-3 border-b border-zinc-800 bg-zinc-900/20 flex justify-between items-center">
                    <span className="text-[11px] font-bold uppercase tracking-wider font-mono flex items-center gap-1.5 text-zinc-300">
                      <Eye className="h-4 w-4 text-blue-500" />
                      Browser Screen Proof
                    </span>
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-zinc-400 hover:text-zinc-50 hover:bg-zinc-800/50" onClick={() => setShowScreenshotModal(true)}>
                      <Maximize2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                  <div className="p-3 bg-zinc-950/40">
                    <div 
                      className="relative rounded-xl overflow-hidden border border-zinc-800/60 cursor-pointer shadow-inner bg-zinc-950/80 group-hover:border-zinc-700 transition-all duration-300"
                      onClick={() => setShowScreenshotModal(true)}
                    >
                      <img 
                        src={getScreenshotUrl(selectedEmail.screenshot)} 
                        alt="Playwright verify" 
                        className="w-full h-auto object-cover max-h-48 group-hover:scale-[1.01] transition-transform duration-300" 
                      />
                      <div className="absolute inset-0 bg-zinc-950/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-zinc-200 text-xs font-semibold tracking-wider uppercase font-mono backdrop-blur-xs">
                        Expand Telemetry Screenshot
                      </div>
                    </div>
                  </div>
                </Card>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 border border-dashed border-zinc-800 rounded-2xl flex flex-col items-center justify-center text-zinc-500 bg-zinc-900/5 backdrop-blur-xs h-full p-8 shadow-inner">
            <Mail className="h-10 w-10 text-zinc-700 mb-3 animate-pulse" />
            <h3 className="font-bold text-xs uppercase tracking-wider font-mono text-zinc-400 mb-1">Queue Dispatch Empty</h3>
            <p className="text-[11px] max-w-xs text-center text-zinc-500 leading-relaxed">
              Select a generated outreach candidate from the queue dashboard index to initiate direct applying logs.
            </p>
          </div>
        )}
      </div>

      {/* Screen Proof overlay Fullscreen Modal */}
      <AnimatePresence>
        {showScreenshotModal && selectedEmail?.screenshot && (
          <div className="fixed inset-0 bg-zinc-950/90 flex items-center justify-center z-50 p-4 backdrop-blur-md">
            {/* Backdrop Fade */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-zinc-950/20"
              onClick={() => setShowScreenshotModal(false)}
            />

            {/* Container Spring Modal */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ type: "spring", stiffness: 350, damping: 28 }}
              className="relative max-w-5xl max-h-[85vh] bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col z-10"
            >
              <div className="p-4 bg-zinc-950/80 text-white flex justify-between items-center border-b border-zinc-800">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider font-mono">
                  <FileText className="h-4.5 w-4.5 text-blue-500" />
                  <span>Screen Proof Telemetry - {selectedEmail.business_name}</span>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setShowScreenshotModal(false)}
                  className="text-zinc-400 hover:text-zinc-50 text-xs hover:bg-zinc-800 font-semibold"
                >
                  Close (ESC)
                </Button>
              </div>
              <div className="overflow-auto bg-zinc-950 p-4 flex items-center justify-center flex-1">
                <img 
                  src={getScreenshotUrl(selectedEmail.screenshot)} 
                  alt="Playwright verify full screen" 
                  className="max-w-full h-auto rounded-xl border border-zinc-800/80 shadow-2xl" 
                />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
