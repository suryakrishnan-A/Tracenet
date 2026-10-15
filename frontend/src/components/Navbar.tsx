'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  Key,
  Terminal,
  LayoutDashboard,
  AlertTriangle,
  Server,
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { ApiKeyModal } from './ApiKeyModal';

interface NavbarProps {
  backendReachable?: boolean;
  onKeyChanged?: () => void;
}

export function Navbar({ backendReachable, onKeyChanged }: NavbarProps) {
  const pathname = usePathname();
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
  const [apiKey, setApiKey] = useState<string | null>(null);

  useEffect(() => {
    setApiKey(apiClient.getApiKey());
  }, []);

  const handleKeyChanged = (newKey: string | null) => {
    setApiKey(newKey);
    if (onKeyChanged) onKeyChanged();
  };

  const navItems = [
    { name: 'Overview', href: '/', icon: LayoutDashboard },
    { name: 'Issues', href: '/issues', icon: AlertTriangle },
  ];

  const maskedKey = apiKey
    ? `${apiKey.slice(0, 10)}...${apiKey.slice(-4)}`
    : null;

  return (
    <>
      <header className="border-b border-slate-800 bg-[#070b14]/90 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="h-9 w-9 rounded-lg bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400 group-hover:border-blue-500/40 transition">
                <Activity className="h-5 w-5" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base tracking-tight text-white group-hover:text-blue-400 transition">
                  TraceNest
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  Incident Engine
                </span>
              </div>
            </Link>

            {/* Navigation Links */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive =
                  item.href === '/'
                    ? pathname === '/'
                    : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                      isActive
                        ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            {/* API Key Switcher Button */}
            <button
              onClick={() => setIsKeyModalOpen(true)}
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono transition ${
                apiKey
                  ? 'bg-slate-900 border-slate-700/80 text-slate-300 hover:border-blue-500/50'
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20'
              }`}
              title="Configure Project API Key"
            >
              <Key className="h-3.5 w-3.5 text-blue-400" />
              <span className="hidden sm:inline">
                {maskedKey ? maskedKey : 'Set API Key'}
              </span>
              <span className="sm:hidden">
                {maskedKey ? 'Key Active' : 'No Key'}
              </span>
            </button>

            {/* Backend Connectivity Status */}
            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
              <span
                className={`h-2 w-2 rounded-full ${
                  backendReachable === true
                    ? 'bg-emerald-400 animate-pulse'
                    : backendReachable === false
                    ? 'bg-rose-500'
                    : 'bg-amber-400'
                }`}
              />
              <span className="text-slate-400 font-mono hidden sm:inline text-[11px]">
                {backendReachable === true
                  ? 'FastAPI Online'
                  : backendReachable === false
                  ? 'Backend Offline'
                  : 'Pinging...'}
              </span>
            </div>

            {/* Swagger Docs Link */}
            <a
              href={`${apiClient.getBaseUrl()}/api/v1/docs`}
              target="_blank"
              rel="noreferrer"
              className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-medium transition border border-slate-700/60"
            >
              <Terminal className="h-3.5 w-3.5 text-slate-400" />
              <span>Swagger</span>
            </a>
          </div>
        </div>
      </header>

      <ApiKeyModal
        isOpen={isKeyModalOpen}
        onClose={() => setIsKeyModalOpen(false)}
        onKeyChanged={handleKeyChanged}
      />
    </>
  );
}
