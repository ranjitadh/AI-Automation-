"use client";

import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { LayoutDashboard, Users, Mail, Settings, Briefcase, Cpu, Radio, Sliders } from 'lucide-react'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname();
  const router = useRouter();

  const navItems = [
    { href: '/', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/businesses', label: 'Businesses', icon: Briefcase },
    { href: '/campaigns', label: 'Campaigns', icon: Users },
    { href: '/outreach', label: 'Outreach', icon: Mail },
  ];

  // Functioning Developer-Grade Keyboard Shortcuts listener
  useEffect(() => {
    let lastKey = '';
    let timeout: any;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore shortcut sequences if user is actively filling form fields
      const activeEl = document.activeElement;
      if (activeEl && (
        activeEl.tagName === 'INPUT' || 
        activeEl.tagName === 'TEXTAREA' || 
        activeEl.tagName === 'SELECT' ||
        activeEl.getAttribute('contenteditable') === 'true'
      )) {
        return;
      }

      const key = e.key.toLowerCase();

      if (lastKey === 'g') {
        if (key === 'd') {
          router.push('/');
          e.preventDefault();
        } else if (key === 'l') {
          router.push('/businesses');
          e.preventDefault();
        } else if (key === 'c') {
          router.push('/campaigns');
          e.preventDefault();
        } else if (key === 'o') {
          router.push('/outreach');
          e.preventDefault();
        } else if (key === 's') {
          router.push('/settings');
          e.preventDefault();
        }
        lastKey = '';
      } else {
        if (key === 'g') {
          lastKey = 'g';
          if (timeout) clearTimeout(timeout);
          // Auto reset buffer after 1 second
          timeout = setTimeout(() => {
            lastKey = '';
          }, 1000);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (timeout) clearTimeout(timeout);
    };
  }, [router]);

  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-zinc-950 text-zinc-50 flex h-screen overflow-hidden relative font-sans`}>
        {/* Ambient Backlight Glows */}
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none z-0" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none z-0" />

        {/* Sidebar */}
        <aside className="w-68 bg-zinc-900/40 backdrop-blur-xl border-r border-zinc-800/80 flex flex-col hidden md:flex z-10">
          {/* Brand/Header */}
          <div className="h-20 flex items-center px-6 border-b border-zinc-800/80 justify-between">
            <div className="flex flex-col">
              <span className="text-[10px] uppercase font-bold tracking-[0.2em] text-blue-500">GurkhasLabs</span>
              <h1 className="text-sm font-black tracking-tight text-zinc-50 bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent flex items-center gap-1.5">
                AI SDR AGENT
              </h1>
            </div>
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 p-4 space-y-2 mt-4 relative">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;

              return (
                <Link 
                  key={item.href}
                  href={item.href} 
                  className={`flex items-center px-4 py-3 text-xs font-semibold rounded-xl transition-all duration-200 group gap-3 relative ${
                    isActive ? 'text-zinc-50' : 'text-zinc-400 hover:text-zinc-50'
                  }`}
                >
                  {/* Gliding Vercel-style Indicator Pill */}
                  {isActive && (
                    <motion.div 
                      layoutId="activeNavIndicator"
                      className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 border-l-2 border-blue-500 rounded-xl z-0"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    />
                  )}
                  <Icon className={`h-4.5 w-4.5 relative z-10 transition-colors ${
                    isActive ? 'text-blue-500' : 'text-zinc-500 group-hover:text-zinc-300'
                  }`} /> 
                  <span className="relative z-10">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Keyboard Shortcuts Navigation Panel */}
          <div className="mx-4 mb-3 p-4 border border-zinc-800/60 bg-zinc-950/60 rounded-2xl font-mono text-[9px] text-zinc-500 space-y-2">
            <div className="text-[10px] text-zinc-400 font-bold tracking-wider font-sans border-b border-zinc-800/60 pb-1.5 flex items-center gap-1.5">
              <Sliders className="h-3.5 w-3.5 text-blue-500" />
              KEYBOARD HOTKEYS
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <span>G + D</span>
                <span className="text-zinc-400 font-sans">Dashboard</span>
              </div>
              <div className="flex justify-between items-center">
                <span>G + L</span>
                <span className="text-zinc-400 font-sans">Leads Registry</span>
              </div>
              <div className="flex justify-between items-center">
                <span>G + C</span>
                <span className="text-zinc-400 font-sans">Campaigns</span>
              </div>
              <div className="flex justify-between items-center">
                <span>G + O</span>
                <span className="text-zinc-400 font-sans">Outreach Console</span>
              </div>
            </div>
          </div>

          {/* AI Console Status Monitor */}
          <div className="p-4 mx-4 mb-4 border border-zinc-800/60 bg-zinc-950/60 rounded-2xl space-y-3 font-mono text-[9px] text-zinc-500">
            <div className="flex justify-between items-center text-zinc-400 border-b border-zinc-800/60 pb-1.5 font-sans font-bold">
              <span className="flex items-center gap-1 text-[10px]">
                <Cpu className="h-3 w-3 text-blue-500" />
                CONSOLE STATUS
              </span>
              <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[8px] px-1.5 py-0.5 rounded font-mono font-bold">
                ONLINE
              </span>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span>AGENT ENGINE</span>
                <span className="text-zinc-300">ACTIVE (IDLE)</span>
              </div>
              <div className="flex justify-between">
                <span>PLAYWRIGHT</span>
                <span className="text-zinc-300">HEADLESS ON</span>
              </div>
              <div className="flex justify-between">
                <span>CELERY DEPLOY</span>
                <span className="text-emerald-400 flex items-center gap-0.5">
                  <Radio className="h-2 w-2 animate-pulse" />
                  CONNECTED
                </span>
              </div>
            </div>
          </div>

          {/* Settings Footer */}
          <div className="p-4 border-t border-zinc-800/80">
            <Link 
              href="/settings" 
              className={`flex items-center px-4 py-3 text-xs font-semibold rounded-xl transition-all duration-200 group gap-3 relative ${
                pathname === '/settings' ? 'text-zinc-50' : 'text-zinc-400 hover:text-zinc-50'
              }`}
            >
              {pathname === '/settings' && (
                <motion.div 
                  layoutId="activeNavIndicator"
                  className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 border-l-2 border-blue-500 rounded-xl z-0"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
              <Settings className={`h-4.5 w-4.5 relative z-10 transition-colors ${
                pathname === '/settings' ? 'text-blue-500' : 'text-zinc-500 group-hover:text-zinc-300'
              }`} /> 
              <span className="relative z-10">Settings</span>
            </Link>
          </div>
        </aside>

        {/* Main Content Workspace with Mount Animations */}
        <main className="flex-1 overflow-y-auto p-8 z-10 relative">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.18, ease: "easeInOut" }}
              className="max-w-7xl mx-auto h-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </body>
    </html>
  )
}
